import { Tour } from './onboarding.types';

/**
 * Definición de tours como DATA. Agregar un tour = una entrada aquí; ningún
 * componente hardcodea pasos. Los selectores apuntan a atributos data-tour="..."
 * puestos en el chrome/hub para no depender de clases de estilo frágiles.
 */
export const TOURS: Record<string, Tour> = {
  'hub-principal': {
    id: 'hub-principal',
    saludo: '¡Hola! Soy Kenny. Te muestro KennedyConecta en 30 segundos.',
    pasos: [
      {
        selector: '[data-tour="menu-toggle"]',
        texto: 'Con este botón abres el menú lateral: desde ahí llegas a cada módulo según tu rol.',
        estadoMascota: 'senalando',
        posicion: 'bottom',
      },
      {
        selector: '[data-tour="hub-cards"]',
        texto: 'Estas tarjetas son tus accesos principales. El flujo de trabajo arranca en "Actividades".',
        estadoMascota: 'senalando',
        posicion: 'top',
      },
      {
        selector: '[data-tour="topbar-perfil"]',
        texto: 'Aquí cambias tu contraseña y cierras sesión. ¡Listo, ya puedes empezar!',
        estadoMascota: 'celebrando',
        posicion: 'bottom',
      },
    ],
  },

  presupuesto: {
    id: 'presupuesto',
    saludo: 'Te muestro el módulo de Presupuesto.',
    pasos: [
      {
        selector: '[data-tour="presupuesto-titulo"]',
        texto: 'Módulo de Presupuesto: aquí vive la cadena Proyecto → Meta → KPI → Contrato → Actividad.',
        estadoMascota: 'saludo',
        posicion: 'bottom',
      },
      {
        selector: '[data-tour="presupuesto-cards"]',
        texto: 'Cada tarjeta abre una operación (proyectos, CDPs, contratos, metas, KPIs). El panel ejecutivo con gráficas está en la card "Dashboard".',
        estadoMascota: 'senalando',
        posicion: 'top',
      },
      {
        selector: '[data-tour="menu-toggle"]',
        texto: 'Desde el menú vuelves a otros módulos. ¡Listo!',
        estadoMascota: 'celebrando',
        posicion: 'bottom',
      },
    ],
  },

  actividades: {
    id: 'actividades',
    saludo: 'Así funcionan las Actividades.',
    pasos: [
      {
        selector: '[data-tour="actividades-titulo"]',
        texto: 'Aquí arranca el trabajo en territorio: cursos, eventos, caracterizaciones, entregas y más.',
        estadoMascota: 'saludo',
        posicion: 'bottom',
      },
      {
        selector: '[data-tour="actividades-tipos"]',
        texto: 'Elige el tipo de actividad y el subgrupo; desde ahí se abre el flujo (Banco, Jóvenes, Caracterización, Cursos…).',
        estadoMascota: 'senalando',
        posicion: 'top',
      },
      {
        selector: '[data-tour="topbar-perfil"]',
        texto: '¡Listo! Puedes repetir este tour cuando quieras haciendo clic en mí.',
        estadoMascota: 'celebrando',
        posicion: 'bottom',
      },
    ],
  },
};
