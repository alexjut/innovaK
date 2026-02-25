def obtener_botones_kactivo(user):
    botones = []

    if user.groups.filter(name='Admin').exists() or user.groups.filter(name='Coordinador').exists():
        botones += [
            ('consulta_participantes_cultura', 'users.png', 'Participantes Cultura', 'cultura'),
            ('crear_curso_cultura', 'plus.png', 'Crear curso Cultura', 'cultura'),
            ('consulta_lugares_cultura', 'map.png', 'Lugares Cultura', 'cultura'),
            ('consulta_asistencia_cultura', 'attendance.png', 'Asistencia Cultura', 'cultura'),
        ]

    if user.groups.filter(name='Docente').exists():
        botones += [
            ('consulta_asistencia_cultura', 'attendance.png', 'Asistencia Cultura', 'cultura'),
        ]

    # Aquí agregas botones de deporte si aplica...
    return botones