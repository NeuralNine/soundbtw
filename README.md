# ️🎙️ soundbtw
Minimal soundboard for Linux, which will hopefully work on Wayland.

### Commands For Permissions

WARNING: These are not optimal and can lead to security issues.

```bash
sudo usermod -aG input $USER

sudo tee /etc/udev/rules.d/99-evdev-input.rules >/dev/null <<'EOF'
KERNEL=="event*", SUBSYSTEM=="input", GROUP="input", MODE="0660"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger
```
