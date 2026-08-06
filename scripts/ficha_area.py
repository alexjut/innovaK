"""Genera la ficha por subgrupo que se adjunta al correo de solicitudes 2026.

    docker exec -i innova_k python manage.py shell < scripts/ficha_area.py

**Solo lectura.** No escribe en la base.

Escribe las fichas **fuera del repositorio**, y no en `docs/`. Motivo: llevan
números y objetos de contrato, y este repositorio es público
(github.com/alexjut/innovaK). El correo que las acompaña sí vive en
`docs/propuestas/correo_areas_solicitudes_2026.md`, porque no lleva datos.

**Ojo con la ruta:** el comando corre DENTRO del contenedor, así que
`/tmp/fichas_area/` es el `/tmp` del contenedor, no el del host. Para sacarlas:

    docker cp innova_k:/tmp/fichas_area ./fichas_area

Solo genera ficha para los subgrupos que **tienen algo**. De los 44 registrados,
37 no tienen ni un proyecto, ni una actividad, ni un evento: mandarles una ficha
en blanco no comunica nada y hace ruido.
"""
import io
import os

from django.db import connection

SALIDA = "/tmp/fichas_area"

CONSULTA_SUBGRUPOS = """
SELECT sg.id, sg.nombre,
  (SELECT COUNT(*) FROM proyecto p WHERE p.subgrupo_id = sg.id)                    AS proyectos,
  (SELECT COUNT(*) FROM actividad_plan ap JOIN proyecto p ON p.id = ap.proyecto_id
    WHERE p.subgrupo_id = sg.id)                                                   AS act_plan,
  (SELECT COUNT(*) FROM evento e WHERE e.subgrupo_id = sg.id)                      AS eventos,
  (SELECT COUNT(*) FROM evento e WHERE e.subgrupo_id = sg.id
    AND EXTRACT(YEAR FROM e.fecha_inicio) = 2026)                                  AS eventos_2026,
  (SELECT COUNT(DISTINCT pe.id) FROM participante_evento pe
     JOIN evento e ON e.id = pe.evento_id WHERE e.subgrupo_id = sg.id)             AS inscritos
FROM subgrupo sg
ORDER BY act_plan DESC, eventos DESC, sg.nombre
"""


def _filas(cur, sql, params=None):
    cur.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def ficha(cur, sg):
    """Texto de la ficha de un subgrupo. Sin cifras inventadas: si no hay, se dice."""
    out = [f"# Ficha de {sg['nombre']} — corte 2026-08-06", ""]
    out.append("Lo que el sistema tiene hoy a nombre de su subgrupo.")
    out.append("")
    out.append("| | |")
    out.append("|---|---|")
    out.append(f"| Proyectos | {sg['proyectos']} |")
    out.append(f"| Actividades del plan | {sg['act_plan']} |")
    out.append(f"| Eventos registrados | {sg['eventos']} |")
    out.append(f"| …de ellos, de 2026 | **{sg['eventos_2026']}** |")
    out.append(f"| Personas inscritas en esos eventos | {sg['inscritos']} |")
    out.append("")

    # ── Plan ────────────────────────────────────────────────────────────
    plan = _filas(cur, """
        SELECT ap.id, LEFT(ap.descripcion, 70) AS descripcion,
               pr.codigo AS proyecto, LEFT(pr.nombre, 40) AS proyecto_nombre,
               (SELECT COUNT(*) FROM actividad_indicador ai
                 WHERE ai.actividad_plan_id = ap.id) AS kpis,
               (SELECT COUNT(*) FROM evento e WHERE e.actividad_plan_id = ap.id) AS eventos
        FROM actividad_plan ap JOIN proyecto pr ON pr.id = ap.proyecto_id
        WHERE pr.subgrupo_id = %s ORDER BY ap.id
    """, [sg["id"]])
    out.append("## Actividades del plan")
    out.append("")
    if plan:
        out.append("| Actividad | Proyecto | Metas | Ejecuciones |")
        out.append("|---|---|---|---|")
        for a in plan:
            marca = "" if a["kpis"] else " ⚠️ sin meta"
            out.append(f"| {a['descripcion']}{marca} | {a['proyecto']} | {a['kpis']} | {a['eventos']} |")
    else:
        out.append("**Ninguna.** El subgrupo no tiene actividades en el plan, así que "
                   "nada de lo que ejecute puede sumar a una meta todavía.")
    out.append("")

    # ── Contratos ───────────────────────────────────────────────────────
    contratos = _filas(cur, """
        SELECT ct.contrato_numero, ct.contrato_vigencia, ct.fecha_inicio, ct.fecha_fin,
               ct.valor, LEFT(COALESCE(ct.objeto, ''), 70) AS objeto,
               (ct.fecha_fin >= CURRENT_DATE) AS al_dia,
               (SELECT COUNT(*) FROM contrato_actividad_plan cap
                 WHERE cap.contrato_id = ct.id AND cap.activo) AS enganches
        FROM contrato ct
        JOIN cdp ON cdp.id = ct.cdp_id
        JOIN proyecto pr ON pr.id = cdp.proyecto_id
        WHERE pr.subgrupo_id = %s ORDER BY ct.fecha_fin DESC NULLS LAST
    """, [sg["id"]])
    out.append("## Contratos que el sistema le atribuye")
    out.append("")
    if contratos:
        out.append("| N.º | Vigencia | Termina | Valor | Enganchado al plan |")
        out.append("|---|---|---|---|---|")
        incompletos = []
        for ct in contratos:
            estado = "sí" if ct["enganches"] else "**NO**"
            fin = str(ct["fecha_fin"]) if ct["fecha_fin"] else "⚠️ sin fecha"
            marca = " (al día)" if ct["al_dia"] else ""
            valor = (f"${ct['valor']:,.0f}" if ct["valor"]
                     else "⚠️ sin valor")
            out.append(f"| {ct['contrato_numero']} | {ct['contrato_vigencia'] or '—'} | "
                       f"{fin}{marca} | {valor} | {estado} |")
            if not ct["fecha_fin"] or not ct["valor"]:
                incompletos.append(str(ct["contrato_numero"]))
        if incompletos:
            # Es lo más accionable de la ficha: el área lo sabe y nosotros no.
            out.append("")
            out.append(f"⚠️ **{len(incompletos)} de estos {len(contratos)} contratos están "
                       f"incompletos** (sin valor, sin fecha de terminación, o ambas): "
                       f"n.º {', '.join(incompletos)}. Sin valor no se puede calcular saldo "
                       f"ni sobre-ejecución; sin fecha de terminación no se sabe si sigue "
                       f"al día. **Ese dato lo tiene el área y nosotros no.**")
    else:
        out.append("**Ninguno.** Ojo: esto **no** quiere decir que el área no tenga "
                   "contratos, sino que ninguno llegó al sistema con su CDP. Sin CDP "
                   "no hay proyecto, y sin proyecto no hay forma de saber de qué área "
                   "es. Es el caso de 20 de los 24 contratos cargados.")
    out.append("")
    out.append("---")
    out.append("")
    out.append("Si algo de esto no cuadra con la realidad del área, es justo lo que "
               "queremos saber. Responda al correo que acompaña esta ficha.")
    return "\n".join(out) + "\n"


def main():
    os.makedirs(SALIDA, exist_ok=True)
    with connection.cursor() as cur:
        subgrupos = _filas(cur, CONSULTA_SUBGRUPOS)
        con_algo = [s for s in subgrupos
                    if s["proyectos"] or s["act_plan"] or s["eventos"]]
        vacios = len(subgrupos) - len(con_algo)

        print(f"Subgrupos registrados: {len(subgrupos)}")
        print(f"  con algún dato: {len(con_algo)}  ->  se genera ficha")
        print(f"  sin nada:       {vacios}  ->  se omiten (una ficha en blanco no dice nada)")
        print()
        for sg in con_algo:
            slug = (sg["nombre"].lower()
                    .replace(" ", "_").replace(",", "").replace("ó", "o")
                    .replace("á", "a").replace("é", "e").replace("í", "i")
                    .replace("ú", "u").replace("ñ", "n"))
            ruta = os.path.join(SALIDA, f"ficha_{slug}.md")
            io.open(ruta, "w", encoding="utf-8").write(ficha(cur, sg))
            print(f"  {sg['nombre']:38} plan={sg['act_plan']:<3} "
                  f"evt={sg['eventos']:<3} 2026={sg['eventos_2026']:<3} -> {ruta}")

    print()
    print(f"Fichas en {SALIDA}/ — FUERA del repositorio, que es público.")


main()
