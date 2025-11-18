#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ui.app import App
from windows import enable_high_dpi

if __name__ == "__main__":
    enable_high_dpi()
    app = App()
    app.mainloop()
