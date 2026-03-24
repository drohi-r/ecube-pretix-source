import logging
from decimal import Decimal
from io import BytesIO
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from ..theme_config import sanitize_filename


try:
    from PIL import ImageCms
except ImportError:  # pragma: no cover
    ImageCms = None


DERIVATIVE_GROUPS = {
    "hero_original": ("hero_card_16x9", "hero_email_banner", "hero_ticket_texture", "thumbnail_square"),
    "thumbnail_override": ("thumbnail_square",),
    "logo_original": ("logo_email", "logo_ticket"),
    "background_texture_original": ("background_texture_web", "background_texture_ticket"),
}


def process_event_asset_pack(asset_pack, changed_fields=None):
    changed_fields = set(changed_fields or ())
    if not changed_fields:
        changed_fields = set(DERIVATIVE_GROUPS.keys())

    generated = {}

    if "hero_original" in changed_fields:
        _process_hero_assets(asset_pack, generated)
    elif "thumbnail_override" in changed_fields:
        _process_thumbnail(asset_pack, generated)

    if "logo_original" in changed_fields:
        _process_logo_assets(asset_pack, generated)

    if "background_texture_original" in changed_fields:
        _process_background_assets(asset_pack, generated)

    asset_pack.processing_meta = {
        "generated": generated,
        "hero_focal_x": str(asset_pack.hero_focal_x),
        "hero_focal_y": str(asset_pack.hero_focal_y),
    }
    asset_pack.save(update_fields=["processing_meta", "updated_at"])
    return asset_pack


def delete_derivatives_for(asset_pack, source_field_name):
    for derivative_name in DERIVATIVE_GROUPS.get(source_field_name, ()):
        _delete_field_file(asset_pack, derivative_name)
    asset_pack.save(update_fields=list(DERIVATIVE_GROUPS.get(source_field_name, ())) + ["updated_at"])


def _process_hero_assets(asset_pack, generated):
    if not getattr(asset_pack.hero_original, "name", ""):
        for name in ("hero_card_16x9", "hero_email_banner", "hero_ticket_texture"):
            _delete_field_file(asset_pack, name)
        _process_thumbnail(asset_pack, generated)
        asset_pack.save(update_fields=["hero_card_16x9", "hero_email_banner", "hero_ticket_texture", "thumbnail_square", "updated_at"])
        return

    with _open_source_image(asset_pack.hero_original) as hero_image:
        focal = (float(asset_pack.hero_focal_x or Decimal("0.50")), float(asset_pack.hero_focal_y or Decimal("0.50")))
        generated["hero_card_16x9"] = _save_jpeg_derivative(
            asset_pack,
            "hero_card_16x9",
            hero_image,
            size=(1600, 900),
            crop=True,
            focal=focal,
            quality=88,
            suffix="hero-card-16x9",
        )
        generated["hero_email_banner"] = _save_jpeg_derivative(
            asset_pack,
            "hero_email_banner",
            hero_image,
            size=(1200, 400),
            crop=True,
            focal=focal,
            quality=86,
            suffix="hero-email-banner",
        )
        generated["hero_ticket_texture"] = _save_jpeg_derivative(
            asset_pack,
            "hero_ticket_texture",
            hero_image,
            size=(2480, 1169),
            crop=True,
            focal=focal,
            quality=84,
            suffix="hero-ticket-texture",
            transform=_ticket_texture_transform,
        )

    _process_thumbnail(asset_pack, generated)
    asset_pack.save(update_fields=["hero_card_16x9", "hero_email_banner", "hero_ticket_texture", "thumbnail_square", "updated_at"])


def _process_thumbnail(asset_pack, generated):
    source = asset_pack.thumbnail_override if getattr(asset_pack.thumbnail_override, "name", "") else asset_pack.hero_original
    if not getattr(source, "name", ""):
        _delete_field_file(asset_pack, "thumbnail_square")
        asset_pack.save(update_fields=["thumbnail_square", "updated_at"])
        return

    focal = (float(asset_pack.hero_focal_x or Decimal("0.50")), float(asset_pack.hero_focal_y or Decimal("0.50")))
    with _open_source_image(source) as thumbnail_image:
        generated["thumbnail_square"] = _save_jpeg_derivative(
            asset_pack,
            "thumbnail_square",
            thumbnail_image,
            size=(800, 800),
            crop=True,
            focal=focal,
            quality=86,
            suffix="thumbnail-square",
        )
    asset_pack.save(update_fields=["thumbnail_square", "updated_at"])


def _process_logo_assets(asset_pack, generated):
    if not getattr(asset_pack.logo_original, "name", ""):
        for name in ("logo_email", "logo_ticket"):
            _delete_field_file(asset_pack, name)
        asset_pack.save(update_fields=["logo_email", "logo_ticket", "updated_at"])
        return

    with _open_source_image(asset_pack.logo_original) as logo_image:
        generated["logo_email"] = _save_png_derivative(
            asset_pack,
            "logo_email",
            logo_image,
            max_width=600,
            suffix="logo-email",
        )
        generated["logo_ticket"] = _save_png_derivative(
            asset_pack,
            "logo_ticket",
            logo_image,
            max_width=1000,
            suffix="logo-ticket",
        )
    asset_pack.save(update_fields=["logo_email", "logo_ticket", "updated_at"])


def _process_background_assets(asset_pack, generated):
    if not getattr(asset_pack.background_texture_original, "name", ""):
        for name in ("background_texture_web", "background_texture_ticket"):
            _delete_field_file(asset_pack, name)
        asset_pack.save(update_fields=["background_texture_web", "background_texture_ticket", "updated_at"])
        return

    with _open_source_image(asset_pack.background_texture_original) as background_image:
        generated["background_texture_web"] = _save_jpeg_derivative(
            asset_pack,
            "background_texture_web",
            background_image,
            max_width=1920,
            quality=84,
            suffix="background-texture-web",
        )
        generated["background_texture_ticket"] = _save_jpeg_derivative(
            asset_pack,
            "background_texture_ticket",
            background_image,
            size=(2480, 1169),
            crop=True,
            focal=(0.5, 0.5),
            quality=84,
            suffix="background-texture-ticket",
        )
    asset_pack.save(update_fields=["background_texture_web", "background_texture_ticket", "updated_at"])


def _open_source_image(field_file):
    field_file.open("rb")
    try:
        image = Image.open(field_file)
        image.load()
    finally:
        field_file.close()
    image = ImageOps.exif_transpose(image)
    image = _convert_to_srgb(image)
    return image


def _convert_to_srgb(image):
    if ImageCms and image.info.get("icc_profile"):
        try:
            src_profile = ImageCms.ImageCmsProfile(BytesIO(image.info["icc_profile"]))
            dest_profile = ImageCms.createProfile("sRGB")
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            return ImageCms.profileToProfile(image, src_profile, dest_profile, outputMode=image.mode)
        except Exception:
            logger.debug("ICC profile conversion failed, falling back to mode conversion")
    if image.mode in ("RGB", "RGBA"):
        return image
    if "A" in image.getbands():
        return image.convert("RGBA")
    return image.convert("RGB")


def _save_jpeg_derivative(asset_pack, field_name, image, size=None, max_width=None, crop=False, focal=(0.5, 0.5), quality=85, suffix="asset", transform=None):
    derived = image.copy()
    if crop and size:
        derived = _crop_to_aspect(derived, size[0], size[1], focal=focal)
        derived = derived.resize(size, Image.Resampling.LANCZOS)
    elif size:
        derived.thumbnail(size, Image.Resampling.LANCZOS)
    elif max_width and derived.width > max_width:
        height = max(1, round((max_width / derived.width) * derived.height))
        derived = derived.resize((max_width, height), Image.Resampling.LANCZOS)

    if transform is not None:
        derived = transform(derived)

    if derived.mode != "RGB":
        derived = derived.convert("RGB")

    output = BytesIO()
    derived.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
    name = _derivative_name(asset_pack, suffix, ".jpg")
    _replace_field_file(asset_pack, field_name, name, output.getvalue())
    return getattr(asset_pack, field_name).name


def _save_png_derivative(asset_pack, field_name, image, max_width, suffix):
    derived = image.copy()
    if derived.width > max_width:
        height = max(1, round((max_width / derived.width) * derived.height))
        derived = derived.resize((max_width, height), Image.Resampling.LANCZOS)
    if derived.mode not in ("RGBA", "LA"):
        if "A" in derived.getbands():
            derived = derived.convert("RGBA")
        else:
            derived = derived.convert("RGBA")

    output = BytesIO()
    derived.save(output, format="PNG", optimize=True)
    name = _derivative_name(asset_pack, suffix, ".png")
    _replace_field_file(asset_pack, field_name, name, output.getvalue())
    return getattr(asset_pack, field_name).name


def _crop_to_aspect(image, width, height, focal=(0.5, 0.5)):
    target_ratio = width / height
    image_ratio = image.width / image.height
    focal_x = min(max(focal[0], 0.0), 1.0)
    focal_y = min(max(focal[1], 0.0), 1.0)

    if image_ratio > target_ratio:
        crop_width = int(round(image.height * target_ratio))
        left = int(round((image.width - crop_width) * focal_x))
        left = max(0, min(left, image.width - crop_width))
        return image.crop((left, 0, left + crop_width, image.height))

    crop_height = int(round(image.width / target_ratio))
    top = int(round((image.height - crop_height) * focal_y))
    top = max(0, min(top, image.height - crop_height))
    return image.crop((0, top, image.width, top + crop_height))


def _ticket_texture_transform(image):
    image = image.filter(ImageFilter.GaussianBlur(radius=2.8))
    image = ImageEnhance.Brightness(image).enhance(0.72)
    return image


def _derivative_name(asset_pack, suffix, extension):
    event_slug = getattr(asset_pack.event, "slug", "event")
    base = sanitize_filename(event_slug)
    return f"{base}-{suffix}{extension}"


def _replace_field_file(asset_pack, field_name, target_name, content):
    field = getattr(asset_pack, field_name)
    if getattr(field, "name", ""):
        field.delete(save=False)
    field.save(target_name, ContentFile(content), save=False)


def _delete_field_file(asset_pack, field_name):
    field = getattr(asset_pack, field_name)
    if getattr(field, "name", ""):
        field.delete(save=False)
