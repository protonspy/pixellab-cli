import base64
import struct

import pytest

from pixellab_cli.images import EncodedImage, decode, encode, encode_file, read_size


def png_bytes(width: int, height: int) -> bytes:
    """The first 24 bytes of a PNG are enough to carry a size."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height)


def jpeg_bytes(width: int, height: int) -> bytes:
    # SOI, then an APP0 segment to skip over, then an SOF0 carrying the size.
    app0 = b"\xff\xe0" + struct.pack(">H", 4) + b"\x00\x00"
    sof0 = b"\xff\xc0" + struct.pack(">H", 11) + b"\x08" + struct.pack(">HH", height, width)
    return b"\xff\xd8" + app0 + sof0 + b"\x00\x00\x00"


class TestReadSize:
    def test_a_png_size_is_read_from_the_header(self):
        assert read_size(png_bytes(64, 32)) == (64, 32)

    def test_a_jpeg_size_is_read_from_the_frame_header(self):
        assert read_size(jpeg_bytes(128, 96)) == (128, 96)

    def test_an_unrecognised_format_reports_no_size_rather_than_guessing(self):
        assert read_size(b"GIF89a....") is None

    def test_a_truncated_png_reports_no_size(self):
        assert read_size(b"\x89PNG\r\n\x1a\n") is None

    def test_a_jpeg_with_no_frame_header_reports_no_size(self):
        assert read_size(b"\xff\xd8" + b"\x00" * 40) is None


class TestEncode:
    def test_encoding_carries_the_size_it_could_read(self):
        encoded = encode(png_bytes(64, 32))

        assert (encoded.width, encoded.height) == (64, 32)

    def test_encoding_an_unreadable_format_leaves_the_size_unknown(self):
        encoded = encode(b"GIF89a....", "gif")

        assert encoded.width is None
        assert encoded.height is None

    def test_the_payload_is_the_object_the_api_expects(self):
        payload = encode(png_bytes(16, 16)).as_payload()

        assert payload["type"] == "base64"
        assert payload["format"] == "png"
        assert base64.b64decode(payload["base64"]).startswith(b"\x89PNG")

    def test_a_round_trip_returns_the_original_bytes(self):
        data = png_bytes(16, 16)

        assert decode(encode(data).as_payload()) == data


class TestEncodeFile:
    def test_a_png_on_disk_is_encoded_with_its_size(self, tmp_path):
        path = tmp_path / "sprite.png"
        path.write_bytes(png_bytes(48, 48))

        encoded = encode_file(path)

        assert encoded.format == "png"
        assert (encoded.width, encoded.height) == (48, 48)

    def test_a_jpg_extension_is_normalised_to_the_format_the_api_names(self, tmp_path):
        path = tmp_path / "concept.jpg"
        path.write_bytes(jpeg_bytes(32, 32))

        assert encode_file(path).format == "jpeg"

    def test_a_file_with_no_extension_is_treated_as_png(self, tmp_path):
        path = tmp_path / "sprite"
        path.write_bytes(png_bytes(8, 8))

        assert encode_file(path).format == "png"


class TestDecode:
    def test_a_bare_base64_string_decodes(self):
        assert decode(base64.b64encode(b"hello").decode()) == b"hello"

    def test_a_data_uri_prefix_is_stripped(self):
        payload = "data:image/png;base64," + base64.b64encode(b"hello").decode()

        assert decode(payload) == b"hello"

    def test_an_empty_payload_is_an_error_rather_than_an_empty_file(self):
        with pytest.raises(ValueError):
            decode({"type": "base64", "base64": ""})

    def test_a_payload_that_is_not_an_image_is_an_error(self):
        with pytest.raises(ValueError):
            decode(None)


class TestEncodedImage:
    def test_the_dimensions_are_visible_to_the_validator(self):
        # validate._dimensions reads .width and .height off whatever it is given.
        image = EncodedImage(base64="", width=256, height=256)

        assert (image.width, image.height) == (256, 256)
