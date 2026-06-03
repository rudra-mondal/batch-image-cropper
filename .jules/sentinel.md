## 2024-06-03 - Unbounded Image Resizing Denial of Service
**Vulnerability:** The application allowed users to specify arbitrarily large output dimensions (e.g., 100,000 x 100,000 pixels) which were passed directly to `Pillow.Image.resize()`. This leads to immediate memory exhaustion and application crash (OOM kill).
**Learning:** Even desktop applications are vulnerable to resource exhaustion DoS if they allocate memory proportional to unvalidated user inputs. Pillow protects against reading large images, but not against resizing to them.
**Prevention:** Always enforce reasonable upper bounds on image dimensions derived from user input before passing them to image processing libraries.

## 2024-06-03 - File Descriptor Leak and Error Information Disclosure
**Vulnerability:** `Image.open()` was used without explicitly closing the file or using a context manager, leading to potential file descriptor exhaustion. Additionally, raw exception objects were displayed directly in the UI.
**Learning:** Lazy-loading image libraries like Pillow keep file handles open. In a batch processing tool, this can quickly hit OS limits. Exposing raw errors leaks implementation details.
**Prevention:** Always use `with Image.open(...) as img:` to ensure deterministic release of file handles. Provide sanitized, user-friendly error messages instead of raw exception strings.
