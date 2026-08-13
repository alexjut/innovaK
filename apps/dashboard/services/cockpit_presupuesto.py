# apps/dashboard/services/cockpit_presupuesto.py
"""
Cockpit ejecutivo del Plan — datos que NO estaban en el dashboard clásico.

Tres lentes, todas ancladas a la cadena obligatoria del proyecto:

    Proyecto → CDP → Contrato → ContratoActividadPlan → ActividadPlan
       ↓                                                    ↓
      Meta → KPI ←──────────────────────────────────── Evento → Beneficiarios

Funciones:
  - ejecucion_financiera(vigencia)  → banda 💰 Plata (contratos reales)
  - beneficiarios_perfil()          → banda 👥 Gente (personas + enfoque)
  - proyectos_cadena(vigencia)      → la cadena completa por proyecto

Todo es additivo: el dashboard clásico (kpis_presupuesto.py) sigue intacto.
Las cifras salen de la BD real; los bloques sin dato hoy (edad, caracterización)
se reportan en 0 para que el front los muestre como "se activan al poblar".
"""
from django.db import connection


def _rows(sql, params=None):
    with connection.cursor() as c:
        c.execute(sql, params or [])
        return c.fetchall()


def _one(sql, params=None):
    with connection.cursor() as c:
        c.execute(sql, params or [])
        return c.fetchone()


# ---------------------------------------------------------------------------
# 💰 PLATA — ejecución financiera (lente de contratos, no de CDP)
# ---------------------------------------------------------------------------
def ejecucion_financiera(vigencia=None):
    """
    Resumen de plata desde `contrato` (la fuente con valores reales).

    No se usa "saldo = asignado − comprometido" porque hoy solo 1 de 5 CDPs
    tiene valor cargado y daría un saldo negativo absurdo. La lente válida es
    el contratado + % de ejecución física ponderado por valor.
    """
    where = "WHERE 1=1"
    params = []
    if vigencia:
        where += " AND contrato_vigencia = %s"
        params.append(int(vigencia))

    n, n_val, total, num_ejec, den_ejec = _one(
        f"""
        SELECT
            COUNT(*),
            COUNT(valor),
            COALESCE(SUM(valor), 0),
            COALESCE(SUM(CASE WHEN ejecucion IS NOT NULL AND valor IS NOT NULL
                              THEN valor * ejecucion END), 0),
            COALESCE(SUM(CASE WHEN ejecucion IS NOT NULL AND valor IS NOT NULL
                              THEN valor END), 0)
        FROM contrato {where}
        """,
        params,
    )
    pct_ejecucion = round(float(num_ejec) / float(den_ejec), 1) if den_ejec else 0.0

    # Agrupado por ÁREA, no por `categoria`.
    #
    # `contrato.categoria` es la taxonomía de OBRA —VIAS, PARQUES,
    # INTERVENTORIA— y solo la llevan los contratos de Infraestructura: 21 de
    # los 25 caían en «Sin categoría», incluido el convenio de Educación. El
    # gráfico mostraba una torta dominada por un vacío que no significa nada.
    #
    # El área sí está en la cadena y se deduce: contrato → contrato_proyecto →
    # proyecto → subgrupo. Es la misma derivación con la que se llenó
    # `metas.sector`, y hace que el tablero se lea por quien ejecuta.
    #
    # Los que aún no cuelgan de un proyecto quedan como «Sin área asignada»:
    # se muestran, porque esconderlos haría que el total no cuadre con la suma
    # de la torta, y ese descuadre es imposible de explicar en una reunión.
    por_categoria = [
        {
            "categoria": area or "Sin área asignada",
            "n": ncat,
            "valor": float(vcat or 0),
            "ejecucion": float(ej) if ej is not None else None,
        }
        for area, ncat, vcat, ej in _rows(
            f"""
            SELECT s.nombre, COUNT(*), COALESCE(SUM(c.valor), 0),
                   ROUND(AVG(c.ejecucion), 1)
            FROM contrato c
            LEFT JOIN contrato_proyecto cp ON cp.contrato_id = c.id
            LEFT JOIN proyecto p ON p.id = cp.proyecto_id
            LEFT JOIN subgrupo s ON s.id = p.subgrupo_id
            {where.replace("contrato_vigencia", "c.contrato_vigencia")}
            GROUP BY s.nombre
            ORDER BY 3 DESC
            """,
            params,
        )
    ]

    top_proyectos = [
        {
            "codigo": cod or "—",
            "nombre": (nom or "Sin proyecto asignado")[:70],
            "n": np,
            "valor": float(vp or 0),
        }
        for cod, nom, np, vp in _rows(
            f"""
            SELECT proyecto_codigo, proyecto_nombre, COUNT(*),
                   COALESCE(SUM(valor), 0)
            FROM contrato {where}
            GROUP BY proyecto_codigo, proyecto_nombre
            ORDER BY 4 DESC
            LIMIT 6
            """,
            params,
        )
    ]

    cdp_n, cdp_val, cdp_sum = _one(
        "SELECT COUNT(*), COUNT(valor), COALESCE(SUM(valor), 0) FROM cdp"
    )

    vigencias = [
        int(v) for (v,) in _rows(
            "SELECT DISTINCT contrato_vigencia FROM contrato "
            "WHERE contrato_vigencia IS NOT NULL ORDER BY contrato_vigencia DESC"
        )
    ]

    return {
        "contratado_total": float(total or 0),
        "n_contratos": n,
        "n_con_valor": n_val,
        "pct_ejecucion": pct_ejecucion,
        "cdp_asignado": float(cdp_sum or 0),
        "cdp_n": cdp_n,
        "cdp_con_valor": cdp_val,
        "por_categoria": por_categoria,
        "top_proyectos": top_proyectos,
        "vigencias": vigencias,
        "vigencia_activa": int(vigencia) if vigencia else None,
    }


# ---------------------------------------------------------------------------
# 👥 GENTE — perfil de beneficiarios (enfoque diferencial real)
# ---------------------------------------------------------------------------
def beneficiarios_perfil():
    """
    Personas/organizaciones atendidas + desagregación por género (dato real:
    62% mujeres). Edad e identidad de género hoy están vacías → se devuelven
    en 0 para que el front los muestre como "se activan al caracterizar".
    """
    por_tipo = {t: n for t, n in _rows(
        "SELECT tipo, COUNT(*) FROM beneficiario WHERE activo GROUP BY tipo"
    )}
    beneficiarios = por_tipo.get("PERSONA", 0)
    organizaciones = por_tipo.get("ORGANIZACION", 0)

    genero = [
        {"nombre": nom or "Sin dato", "total": tot}
        for nom, tot in _rows(
            """
            SELECT s.nombre, COUNT(*)
            FROM beneficiario b
            JOIN persona p ON p.id = b.persona_id
            LEFT JOIN sexo s ON s.codigo = p.sexo_biologico
            WHERE b.activo AND b.tipo = 'PERSONA'
            GROUP BY s.nombre
            ORDER BY 2 DESC
            """
        )
    ]
    total_gen = sum(g["total"] for g in genero) or 0
    mujeres = next((g["total"] for g in genero if (g["nombre"] or "").lower().startswith("fem")), 0)
    pct_mujeres = round(mujeres / total_gen * 100, 1) if total_gen else 0.0

    participantes, eventos_part = _one(
        "SELECT COUNT(*), COUNT(DISTINCT evento_id) FROM participante_evento"
    )
    por_estado = [
        {"estado": est or "—", "total": tot}
        for est, tot in _rows(
            "SELECT estado, COUNT(*) FROM participante_evento GROUP BY estado ORDER BY 2 DESC"
        )
    ]

    caracterizaciones = sum(
        _one(f"SELECT COUNT(*) FROM caracterizacion_{t}")[0]
        for t in ("cultura", "deporte", "mujer", "salud",
                  "poblacional", "participacion_ciudadana")
    )

    return {
        "beneficiarios": beneficiarios,
        "organizaciones": organizaciones,
        "genero": genero,
        "pct_mujeres": pct_mujeres,
        "participantes": participantes or 0,
        "eventos_con_participacion": eventos_part or 0,
        "participantes_por_estado": por_estado,
        "caracterizaciones": caracterizaciones,
    }


# ---------------------------------------------------------------------------
# 🔗 CADENA — todo lo que pasa en cada proyecto (lo que el alcalde recorre)
# ---------------------------------------------------------------------------
def proyectos_cadena(vigencia=None):
    """
    Rollup por proyecto de la cadena completa, en una pasada de agregados que
    se cruzan en Python por id/codigo. Cada fila trae:

        dinero (contratos + % ejec) · cdp · metas · KPIs (avance) ·
        actividades · eventos · beneficiarios

    Es la vista "trazabilidad de punta a punta" que pidió el alcalde. El
    detalle profundo de cada proyecto ya existe en el 360°
    (/app/presupuesto/proyectos/<id>).
    """
    proyectos = _rows(
        "SELECT id, codigo, nombre, subgrupo_id FROM proyecto ORDER BY codigo NULLS LAST, id"
    )

    cwhere, cparams = "", []
    if vigencia:
        cwhere = "WHERE contrato_vigencia = %s"
        cparams = [int(vigencia)]

    # Dinero por proyecto (clave = proyecto_codigo)
    dinero = {}
    for cod, val, num_e, den_e, ncon in _rows(
        f"""
        SELECT proyecto_codigo,
               COALESCE(SUM(valor), 0),
               COALESCE(SUM(CASE WHEN ejecucion IS NOT NULL AND valor IS NOT NULL
                                 THEN valor * ejecucion END), 0),
               COALESCE(SUM(CASE WHEN ejecucion IS NOT NULL AND valor IS NOT NULL
                                 THEN valor END), 0),
               COUNT(*)
        FROM contrato {cwhere}
        GROUP BY proyecto_codigo
        """,
        cparams,
    ):
        if cod:
            dinero[str(cod)] = {
                "contratado": float(val or 0),
                "ejecucion": round(float(num_e) / float(den_e), 1) if den_e else None,
                "n_contratos": ncon,
            }

    # CDP por proyecto (clave = proyecto_id)
    cdp = {pid: float(v or 0) for pid, v in _rows(
        "SELECT proyecto_id, COALESCE(SUM(valor), 0) FROM cdp "
        "WHERE proyecto_id IS NOT NULL GROUP BY proyecto_id"
    )}

    # Metas + KPIs + avance por proyecto (clave = proyecto_id)
    metas = {}
    for pid, n_mp, n_kpi, meta_sum, avance_sum in _rows(
        """
        SELECT mp.proyecto_id,
               COUNT(DISTINCT mp.id),
               COUNT(DISTINCT imp.id),
               COALESCE(SUM(imp.meta_magnitud), 0),
               COALESCE(SUM(sub.avance), 0)
        FROM meta_proyecto mp
        LEFT JOIN presu_indicador_meta_proyecto imp
               ON imp.meta_proyecto_id = mp.id AND imp.activo = TRUE
        LEFT JOIN (
            SELECT indicador_id, SUM(magnitud_aportada) AS avance
            FROM presu_avance_ind_periodo WHERE activo = TRUE
            GROUP BY indicador_id
        ) sub ON sub.indicador_id = imp.id
        WHERE mp.proyecto_id IS NOT NULL
        GROUP BY mp.proyecto_id
        """
    ):
        meta_f = float(meta_sum or 0)
        av_f = float(avance_sum or 0)
        metas[pid] = {
            "n_metas": n_mp,
            "n_kpis": n_kpi,
            "avance_pct": round(av_f / meta_f * 100, 1) if meta_f > 0 else 0.0,
        }

    # Actividades del plan por proyecto
    actividades = {pid: n for pid, n in _rows(
        "SELECT proyecto_id, COUNT(*) FROM actividad_plan "
        "WHERE proyecto_id IS NOT NULL GROUP BY proyecto_id"
    )}

    # Eventos por proyecto (vía actividad_plan)
    eventos = {pid: n for pid, n in _rows(
        """
        SELECT ap.proyecto_id, COUNT(DISTINCT e.id)
        FROM actividad_plan ap
        JOIN evento e ON e.actividad_plan_id = ap.id
        WHERE e.activo IS NOT FALSE AND ap.proyecto_id IS NOT NULL
        GROUP BY ap.proyecto_id
        """
    )}

    # Beneficiarios por proyecto — TODAS las formas de atender a alguien.
    #
    # Hasta el 2026-08-13 esto contaba solo `participante_evento`, o sea las
    # inscripciones a cursos. Cualquier módulo que capture a su gente por su
    # cuenta —becas, entregas de insumos, capturas genéricas— quedaba en CERO:
    # Educación mostraba 0 beneficiarios teniendo 174 cargados y validados.
    #
    # Se unifica por PERSONA, no por fila: quien aparece en dos módulos es una
    # persona. Por eso todas las fuentes se resuelven a `persona_id` —
    # `participante_evento` llega por su participante— y se cuenta DISTINCT.
    # Contar por documento sería equivalente, pero `participante_evento` no lo
    # guarda y forzaría un join más.
    #
    # Solo entra lo VALIDADO: una entrega enviada y no revisada todavía no es
    # una persona atendida, y contarla inflaría el tablero con lo que está en
    # revisión.
    benef = {pid: n for pid, n in _rows(
        """
        SELECT ap.proyecto_id, COUNT(DISTINCT x.persona_id)
        FROM actividad_plan ap
        JOIN evento e ON e.actividad_plan_id = ap.id
        JOIN (
            SELECT pe.evento_id, p.persona_id
              FROM participante_evento pe
              JOIN participante p ON p.id = pe.participante_id
            UNION ALL
            SELECT evento_id, persona_id FROM entrega_beca     WHERE estado = 'validada'
            UNION ALL
            SELECT evento_id, persona_id FROM entrega_insumo   WHERE estado = 'validada'
            UNION ALL
            SELECT evento_id, persona_id FROM captura_generica WHERE estado = 'validada'
        ) x ON x.evento_id = e.id
        WHERE ap.proyecto_id IS NOT NULL AND x.persona_id IS NOT NULL
        GROUP BY ap.proyecto_id
        """
    )}

    filas = []
    for pid, cod, nom, _sub in proyectos:
        d = dinero.get(str(cod)) if cod else None
        m = metas.get(pid, {})
        fila = {
            "id": pid,
            "codigo": cod or "—",
            "nombre": (nom or f"Proyecto {pid}").strip(),
            "contratado": d["contratado"] if d else 0.0,
            "ejecucion": d["ejecucion"] if d else None,
            "n_contratos": d["n_contratos"] if d else 0,
            "cdp": cdp.get(pid, 0.0),
            "n_metas": m.get("n_metas", 0),
            "n_kpis": m.get("n_kpis", 0),
            "avance_pct": m.get("avance_pct", 0.0),
            "n_actividades": actividades.get(pid, 0),
            "n_eventos": eventos.get(pid, 0),
            "n_beneficiarios": benef.get(pid, 0),
        }
        filas.append(fila)

    # Orden: primero los que mueven plata, luego por avance
    filas.sort(key=lambda f: (f["contratado"], f["avance_pct"]), reverse=True)

    return {
        "proyectos": filas,
        "totales": {
            "n_proyectos": len(filas),
            "contratado": sum(f["contratado"] for f in filas),
            "beneficiarios": sum(f["n_beneficiarios"] for f in filas),
            "eventos": sum(f["n_eventos"] for f in filas),
        },
    }
