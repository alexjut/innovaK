"""Vistas del módulo Presupuesto.

Paquete vacío a propósito: cada vista se importa desde su submódulo
(`.catalogo`, `.contratos`, `.cdp`, `.metas`, `.indicadores`, `.api`).

Acá vivía un script de depuración de cinco líneas —`django.setup()` + un
`print('OK Proyecto:', …)`— que entró el 2025-09-02 y se quedó once meses.
Como `apps/presupuesto/urls.py` importa de este paquete, se ejecutaba en el
arranque de CADA proceso: reentraba a `django.setup()` mientras Django todavía
estaba cargando las URLs, y ensuciaba la salida de todos los comandos de
management. No borrar esta nota: el archivo se ve inofensivo justamente por
estar vacío, y ese es el punto.
"""
