## 2024-10-27 - Added dynamic tooltips for disabled states
**Learning:** PySide6/Qt allows easy and dynamic tooltips using `.setToolTip()`. When buttons are disabled based on complex conditions (like list selection or list length), users can be left guessing why.
**Action:** Always consider using dynamic tooltips for critical action buttons that change state. Extracting boolean conditions into readable variables makes updating tooltips and button states easier simultaneously.
