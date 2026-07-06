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
};
