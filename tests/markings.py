"""Test files carrying a Marking, built at test time: nothing is fetched.

XMP packets are written into PNG, JPEG and WebP with Pillow, and into MP4 and
MOV as the boxes Adobe's XMP specification (part 3) names: a top-level `uuid`
box for MP4, `moov/udta/XMP_` for QuickTime. C2PA manifests are signed with
c2pa-python by a throwaway certificate chain made here with `cryptography`:
the signature validates, but no trust list knows the signer.
"""

from __future__ import annotations

import datetime as dt
import io
import struct
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from helpers import BACKGROUND

IPTC_SOURCE = "http://cv.iptc.org/newscodes/digitalsourcetype/"
XMP_UUID = bytes.fromhex("BE7ACFCB97A942E89C71999491E3AFAC")


def xmp_packet(source_type: str | None = None, creator_tool: str | None = None, software: str | None = None,
               element: bool = False, ai: dict | None = None, instance_id: str | None = None,
               provenance: str | None = None) -> bytes:
    """An XMP packet. `source_type` is an IPTC code (`trainedAlgorithmicMedia`), written as the full URI;
    `element` writes it as an element with rdf:resource rather than as an attribute. `ai` holds IPTC AI
    fields by name (`AISystemUsed`, ...); `instance_id` is an xmpMM:InstanceID and `provenance` a
    dcterms:provenance, neither of which a Labelled Copy may inherit."""
    attributes, elements = [], []
    for name, value in (ai or {}).items():
        elements.append(f"<Iptc4xmpExt:{name}>{value}</Iptc4xmpExt:{name}>")
    if instance_id:
        attributes.append(f'xmpMM:InstanceID="{instance_id}"')
    if provenance:
        attributes.append(f'dcterms:provenance="{provenance}"')
    if source_type and element:
        elements.append(f'<Iptc4xmpExt:DigitalSourceType rdf:resource="{IPTC_SOURCE}{source_type}"/>')
    elif source_type:
        attributes.append(f'Iptc4xmpExt:DigitalSourceType="{IPTC_SOURCE}{source_type}"')
    if creator_tool:
        attributes.append(f'xmp:CreatorTool="{creator_tool}"')
    if software:
        elements.append(f"<tiff:Software>{software}</tiff:Software>")
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
        'xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmlns:tiff="http://ns.adobe.com/tiff/1.0/" '
        'xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/" xmlns:dcterms="http://purl.org/dc/terms/" '
        + " ".join(attributes) + ">" + "".join(elements) +
        "</rdf:Description></rdf:RDF></x:xmpmeta>"
        '<?xpacket end="w"?>'
    ).encode()


def picture(size=(64, 48)) -> Image.Image:
    return Image.new("RGB", size, BACKGROUND)


def png(path: Path, xmp: bytes | None = None, text: dict | None = None, compressed: bool = False,
        size=(64, 48)) -> Path:
    """A PNG with `xmp` in an iTXt chunk and each `text` key/value in a tEXt chunk (zTXt when `compressed`)."""
    info = PngInfo()
    if xmp is not None:
        info.add_itxt("XML:com.adobe.xmp", xmp.decode(), zip=compressed)
    for key, value in (text or {}).items():
        info.add_text(key, value, zip=compressed)
    picture(size).save(path, "PNG", pnginfo=info)
    return path


def png_after_idat(path: Path, key: str, value: str, itxt: bool = False) -> Path:
    """A PNG whose `key` text chunk (iTXt when `itxt`, else tEXt) sits after IDAT, just before IEND, where
    the PNG specification allows it."""
    import zlib

    picture().save(path, "PNG")
    data = path.read_bytes()
    text = key.encode("latin-1") + b"\x00"
    body = (b"iTXt" + text + b"\x00\x00\x00\x00" + value.encode()) if itxt else (b"tEXt" + text + value.encode("latin-1"))
    chunk = struct.pack(">I", len(body) - 4) + body + struct.pack(">I", zlib.crc32(body))
    at = data.rindex(b"IEND") - 4
    path.write_bytes(data[:at] + chunk + data[at:])
    return path


def jpeg(path: Path, xmp: bytes | None = None, software: str | None = None, size=(64, 48)) -> Path:
    """A JPEG with `xmp` in its APP1 XMP segment and `software` as EXIF Software (0x0131)."""
    exif = Image.Exif()
    if software:
        exif[0x0131] = software
    image = picture(size)
    image.save(path, "JPEG", exif=exif.tobytes())
    if xmp is not None:
        data = path.read_bytes()
        payload = b"http://ns.adobe.com/xap/1.0/\x00" + xmp
        segment = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
        path.write_bytes(data[:2] + segment + data[2:])  # right after SOI
    return path


def webp(path: Path, xmp: bytes | None = None, size=(64, 48)) -> Path:
    picture(size).save(path, "WEBP", **({"xmp": xmp} if xmp is not None else {}))
    return path


def box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + kind + payload


def with_mp4_xmp(video: Path, xmp: bytes) -> Path:
    """Append the MP4 XMP box (a top-level `uuid` box) to `video`."""
    with video.open("ab") as out:
        out.write(box(b"uuid", XMP_UUID + xmp))
    return video


def with_quicktime_xmp(video: Path, xmp: bytes) -> Path:
    """Add `moov/udta/XMP_` to `video`, whose `moov` must be its last box (ffmpeg's default): growing it
    then moves no sample, so every chunk offset stays right."""
    data = video.read_bytes()
    at, moov = 0, None
    while at < len(data):
        size, kind = struct.unpack(">I4s", data[at:at + 8])
        if kind == b"moov":
            moov = at
        at += size
    assert moov is not None and at == len(data)
    size = struct.unpack(">I", data[moov:moov + 4])[0]
    assert moov + size == len(data), "moov must be the last box"
    added = box(b"udta", box(b"XMP_", xmp))
    video.write_bytes(data[:moov] + struct.pack(">I", size + len(added)) + data[moov + 4:] + added)
    return video


# --- C2PA ------------------------------------------------------------------------

def certificate_chain() -> tuple[bytes, bytes]:
    """A PEM chain (signer, then its root) and the signer's PEM private key, valid for a month."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    now = dt.datetime.now(dt.timezone.utc)

    def usage(sign: bool) -> x509.KeyUsage:
        return x509.KeyUsage(digital_signature=sign, content_commitment=False, key_encipherment=False,
                             data_encipherment=False, key_agreement=False, key_cert_sign=not sign,
                             crl_sign=not sign, encipher_only=False, decipher_only=False)

    def certificate(subject, issuer, key, signing_key, ca: bool):
        builder = (x509.CertificateBuilder().subject_name(subject).issuer_name(issuer)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=30))
                   .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
                   .add_extension(usage(sign=not ca), critical=True)
                   .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False))
        if not ca:
            builder = (builder
                       .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), critical=False)
                       .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(signing_key.public_key()),
                                      critical=False))
        return builder.sign(signing_key, hashes.SHA256())

    root_key, key = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Marking Test Root")])
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Marking Test Signer"),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Example AI Lab")])
    root = certificate(root_name, root_name, root_key, root_key, ca=True)
    signer = certificate(name, root_name, key, root_key, ca=False)
    pem = serialization.Encoding.PEM
    private = key.private_bytes(pem, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return signer.public_bytes(pem) + root.public_bytes(pem), private


_CHAIN = None


def signer():
    import c2pa

    global _CHAIN
    if _CHAIN is None:
        _CHAIN = certificate_chain()
    chain, private = _CHAIN
    return c2pa.Signer.from_info(c2pa.C2paSignerInfo(b"es256", chain, private, None))


def manifest(*source_types: str, generator: str = "Example Image Generator") -> dict:
    """A manifest whose actions each carry one IPTC digitalSourceType code: the first a `c2pa.created`
    action, the others `c2pa.edited`."""
    actions = [
        {"action": "c2pa.created" if i == 0 else "c2pa.edited", "digitalSourceType": IPTC_SOURCE + code}
        for i, code in enumerate(source_types)
    ]
    return {
        "claim_generator_info": [{"name": generator, "version": "1.0"}],
        "title": "marked",
        "assertions": [{"label": "c2pa.actions", "data": {"actions": actions}}],
    }


def signed(source: Path, target: Path, manifest_definition: dict, mime: str = "image/png") -> Path:
    """`source` signed with `manifest_definition` into `target`."""
    import c2pa

    out = io.BytesIO()
    with source.open("rb") as stream, c2pa.Builder(manifest_definition) as builder:
        builder.sign(signer(), mime, stream, out)
    target.write_bytes(out.getvalue())
    return target


def remote_only(source: Path, target: Path, manifest_definition: dict, url: str) -> Path:
    """`source` signed with a manifest kept only at `url`: the file carries the URL, not the manifest."""
    import c2pa

    out = io.BytesIO()
    with source.open("rb") as stream, c2pa.Builder(manifest_definition) as builder:
        builder.set_no_embed()
        builder.set_remote_url(url)
        builder.sign(signer(), "image/png", stream, out)
    target.write_bytes(out.getvalue())
    return target


def tampered(path: Path) -> Path:
    """Insert a text chunk before IEND, after signing: the PNG stays valid and the manifest stays, but the
    hash it holds of the file's bytes no longer matches."""
    import zlib

    data = path.read_bytes()
    at = data.rindex(b"IEND") - 4
    body = b"tEXt" + b"Comment\x00edited after signing"
    chunk = struct.pack(">I", len(body) - 4) + body + struct.pack(">I", zlib.crc32(body))
    path.write_bytes(data[:at] + chunk + data[at:])
    return path
