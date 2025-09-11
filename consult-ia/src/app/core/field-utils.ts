export function pathToSection(path: string): string {
  if (path.startsWith('signos')) return 'Signos vitales';
  if (path.startsWith('examenClinico')) return 'Examen clínico';
  if (path.startsWith('diagnostico')) return 'Diagnóstico';
  if (path.startsWith('tratamiento')) return 'Tratamiento';
  if (path.startsWith('firma')) return 'Firma';
  return 'Otros';
}

export function shortLabel(path: string): string {
  const p = path.split('.').pop() || path;
  return p
    .replace(/([A-Z])/g, ' $1')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, m => m.toUpperCase());
}
