# -*- coding: utf-8 -*-
"""Registro de la interfaz wxPython en la capa de plataforma (app.core.plataforma)."""

import logging

import wx

from app.core.plataforma import registrar_interfaz

log = logging.getLogger(__name__)


def _aviso(texto: str, titulo: str = None):
    app = wx.GetApp()
    if app is None:
        return
    dlg = wx.MessageDialog(app.GetTopWindow(), texto, titulo or "SocialRSS Accessible Suite",
                           wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()


def _toast(texto: str, titulo: str = None):
    import wx.adv
    if wx.GetApp() is None:
        return
    n = wx.adv.NotificationMessage(titulo or "SocialRSS", texto)
    try:
        n.SetFlags(wx.ICON_INFORMATION)
    except Exception:
        pass
    n.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)


def _confirmar(texto: str, titulo: str = "") -> bool:
    dlg = wx.MessageDialog(None, texto, titulo or "SocialRSS",
                           wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
    try:
        return dlg.ShowModal() == wx.ID_YES
    finally:
        dlg.Destroy()


def _copiar(texto: str) -> bool:
    if not wx.TheClipboard.Open():
        return False
    try:
        wx.TheClipboard.SetData(wx.TextDataObject(texto))
        wx.TheClipboard.Flush()
        return True
    finally:
        wx.TheClipboard.Close()


def forzar_primer_plano(window):
    """Fuerza a la ventana a situarse en el primer plano absoluto del sistema operativo,
    superando las restricciones de cambio de foco de Windows Explorer u otras aplicaciones."""
    if not window:
        return
    try:
        window.Raise()
        window.SetFocus()
    except Exception:
        pass

    import sys
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hwnd = window.GetHandle()
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                fg_hwnd = user32.GetForegroundWindow()
                if fg_hwnd and fg_hwnd != hwnd:
                    fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
                    curr_thread = kernel32.GetCurrentThreadId()
                    if fg_thread and fg_thread != curr_thread:
                        user32.AttachThreadInput(curr_thread, fg_thread, True)
                        user32.SetForegroundWindow(hwnd)
                        user32.BringWindowToTop(hwnd)
                        user32.SwitchToThisWindow(hwnd, True)
                        user32.AttachThreadInput(curr_thread, fg_thread, False)
                    else:
                        user32.SetForegroundWindow(hwnd)
                        user32.BringWindowToTop(hwnd)
                        user32.SwitchToThisWindow(hwnd, True)
                else:
                    user32.SetForegroundWindow(hwnd)
                    user32.BringWindowToTop(hwnd)
                    user32.SwitchToThisWindow(hwnd, True)
        except Exception as e:
            log.debug(f"Aviso al forzar primer plano Win32: {e}")


def registrar():
    registrar_interfaz(
        "wx",
        llamar_en_ui=wx.CallAfter,
        es_hilo_ui=wx.IsMainThread,
        hay_interfaz=lambda: wx.GetApp() is not None,
        mostrar_aviso=_aviso,
        mostrar_toast=_toast,
        confirmar=_confirmar,
        # En Windows se conserva win32clipboard (comportamiento original); en otros sistemas, wx.
        copiar=None if __import__("sys").platform == "win32" else _copiar,
    )
