#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script to fix PDF export to use real form data"""

import sys

# Read the file
with open(r'c:\Trabajo\Clinica\Medberos\NewMed\consultia\frontend\src\app\features\consultation-room\consultation-room.component.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start and end of the hardcoded data section
start_marker = '  exportPdf(): void {\n    try {\n      const data = this.formData = {'
end_marker = ';\n      const afiliacion = data.afiliacion || {};'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("ERROR: Could not find markers in file")
    sys.exit(1)

# New code to insert
new_code = '''  exportPdf(): void {
    try {
      // Obtener datos reales del formulario
      const formValue = this.hcForm.getRawValue();

      // Construir estructura de datos para el PDF
      const data = this.formData = {
        afiliacion: {
          nombreCompleto: formValue.afiliacion?.nombreCompleto || '',
          edad: formValue.afiliacion?.edad?.anios || null,
          meses: formValue.afiliacion?.edad?.meses || null,
          sexo: formValue.afiliacion?.sexo || '',
          dni: formValue.afiliacion?.dni || '',
          grupoSangre: formValue.afiliacion?.grupoSangre || '',
          fechaHora: formValue.afiliacion?.fechaHora || '',
          seguro: formValue.afiliacion?.seguro || '',
          tipoConsulta: formValue.afiliacion?.tipoConsulta || '',
          numeroSeguro: formValue.afiliacion?.numeroSeguro || ''
        },
        motivoConsulta: formValue.afiliacion?.motivoConsulta || '',
        anamnesis: {
          tiempoEnfermedad: formValue.anamnesis?.tiempoEnfermedad || '',
          sintomasPrincipales: formValue.anamnesis?.sintomasPrincipales || [],
          relato: formValue.anamnesis?.relato || '',
          funcionesBiologicas: {
            apetito: formValue.anamnesis?.funcionesBiologicas?.apetito || '',
            sed: formValue.anamnesis?.funcionesBiologicas?.sed || '',
            orina: formValue.anamnesis?.funcionesBiologicas?.orina || '',
            deposiciones: formValue.anamnesis?.funcionesBiologicas?.deposiciones || '',
            sueno: formValue.anamnesis?.funcionesBiologicas?.sueno || ''
          },
          personales: {
            padre: formValue.anamnesis?.antecedentes?.padre || [],
            madre: formValue.anamnesis?.antecedentes?.madre || []
          },
          alergias: formValue.anamnesis?.alergias || [],
          medicamentos: formValue.anamnesis?.medicamentos || []
        },
        examenClinico: {
          PA: formValue.examenClinico?.signosVitales?.PA || '',
          FC: formValue.examenClinico?.signosVitales?.FC || null,
          FR: formValue.examenClinico?.signosVitales?.FR || null,
          temperatura: formValue.examenClinico?.signosVitales?.temperatura || '',
          SpO2: formValue.examenClinico?.signosVitales?.SpO2 || '',
          IMC: formValue.examenClinico?.signosVitales?.IMC || '',
          estadoGeneral: formValue.examenClinico?.estadoGeneral || '',
          descripcionGeneral: formValue.examenClinico?.descripcionGeneral || ''
        },
        diagnosticos: formValue.diagnosticos || [],
        examenes: formValue.examenes || [],
        tratamientos: formValue.tratamientos || [],
        interconsultas: formValue.interconsultas || [],
        sugerenciasIA: '',
        camposFaltantes: []
      }'''

# Replace the old code
new_content = content[:start_idx] + new_code + content[end_idx:]

# Write back
with open(r'c:\Trabajo\Clinica\Medberos\NewMed\consultia\frontend\src\app\features\consultation-room\consultation-room.component.ts', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("SUCCESS: Updated exportPdf() to use real form data")
