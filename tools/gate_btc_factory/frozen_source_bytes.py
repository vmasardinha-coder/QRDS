"""Read a pinned source blob across LF/CRLF checkouts without changing its seal."""
import hashlib

def read_frozen_bytes(path,expected_sha256):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()==expected_sha256:return raw
 source=raw.replace(b'\r\n',b'\n')
 if hashlib.sha256(source).hexdigest()!=expected_sha256:raise ValueError('FROZEN_SOURCE_CONTENT_CHANGED')
 return source
