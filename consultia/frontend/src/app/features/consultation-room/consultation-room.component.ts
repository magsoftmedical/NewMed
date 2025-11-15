import { Component, OnDestroy, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { HttpClient, HttpClientModule } from '@angular/common/http';

import { WebSpeechService, WSPartial } from '../../core/web-speech.service';
import { AiStreamService, HistoriaClinica } from '../../core/ai-stream.service';
import { AiStreamPanelComponent } from './ai-stream-panel.component'; // <-- IMPORTA EL PANEL

import jsPDF from 'jspdf';
import autoTable, { RowInput } from 'jspdf-autotable';
import { IconsModule } from '../../icons.module'; // 👈 importa el puente
import { debounceTime } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-consultation-room',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, AiStreamPanelComponent, IconsModule, HttpClientModule],
  templateUrl: './consultation-room.component.html',
  styleUrls: ['./consultation-room.component.scss'],
})
export class ConsultationRoomComponent implements OnInit, OnDestroy {
  // STT (voz-a-texto)
  partialText = '';
  finalText = '';
  listening = false;
  level = 0;
  sessionId = '';

  // IA
  assistantLive = '';            // <- usado en el HTML
  missing: string[] = [];
  suggestions: string[] = [];

  // Tabs del formulario
  activeTab: string = 'afiliacion';
  tabs = [
    { id: 'afiliacion', label: 'Afiliación', icon: '📋' },
    { id: 'anamnesis', label: 'Anamnesis', icon: '🩺' },
    { id: 'examenClinico', label: 'Examen Clínico', icon: '💓' },
    { id: 'diagnosticos', label: 'Diagnósticos', icon: '🏷️' },
    { id: 'tratamientos', label: 'Tratamientos', icon: '💊' },
    { id: 'firma', label: 'Firma', icon: '✍️' }
  ];

  // Reactive Form (Historia Clínica)
  hcForm!: FormGroup;
  formData: any = {};

  // Document upload
  uploading = false;
  extractedDataPreview = '';

  private subs: Subscription[] = [];
  private isBrowser: boolean;

  constructor(
    private wspeech: WebSpeechService,
    public  ai: AiStreamService,
    private fb: FormBuilder,
    private http: HttpClient,
    @Inject(PLATFORM_ID) platformId: Object
  ) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  // Feed de cambios / narración
  deltaFeed: { icon:string; title:string; desc:string; path:string; evidence?:string }[] = [];
  mapPathToTitle(path: string) {
    if (path.startsWith('afiliacion.motivoConsulta')) return { title:'Motivo de consulta', icon:'📋' };
    if (path.startsWith('anamnesis.sintomasPrincipales')) return { title:'Síntomas', icon:'🩺' };
    if (path.startsWith('examenClinico.signosVitales')) return { title:'Signos vitales', icon:'❤️' };
    if (path.startsWith('diagnosticos')) return { title:'Diagnóstico', icon:'🏷️' };
    if (path.startsWith('tratamientos')) return { title:'Tratamiento', icon:'💊' };
    return { title: path, icon:'📌' };
  }

  ngOnInit(): void {
    // 1) Construir formulario reactivo alineado al formato
    this.hcForm = this.fb.group({
      afiliacion: this.fb.group({
        nombreCompleto: [''],
        edad: this.fb.group({ anios: [null], meses: [null] }),
        sexo: [''],
        dni: [''],
        grupoSangre: [''],
        fechaHora: [''],
        seguro: [''],
        tipoConsulta: [''],
        numeroSeguro: [''],
        motivoConsulta: [''],
      }),
      anamnesis: this.fb.group({
        tiempoEnfermedad: [''],
        sintomasPrincipales: this.fb.array<string>([] as any),
        relato: [''],
        funcionesBiologicas: this.fb.group({
          apetito: [''], sed: [''], orina: [''], deposiciones: [''], sueno: [''],
        }),
        antecedentes: this.fb.group({
          personales: this.fb.array<string>([] as any),
          padre: this.fb.array<string>([] as any),
          madre: this.fb.array<string>([] as any),
        }),
        alergias: this.fb.array<string>([] as any),
        medicamentos: this.fb.array<string>([] as any),
      }),
      examenClinico: this.fb.group({
        signosVitales: this.fb.group({
          PA: [''], FC: [null], FR: [null], peso: [null], talla: [null],
          SpO2: [null], temperatura: [null], IMC: [null], glasgow: [null],
        }),
        estadoGeneral: [''],
        descripcionGeneral: [''],
        sistemas: this.fb.group({
          piel: [''], tcs: [''], cabeza: [''], cuello: [''], torax: [''],
          pulmones: [''], corazon: [''], mamasAxilas: [''], abdomen: [''],
          genitoUrinario: [''], rectalPerianal: [''], extremidades: [''],
          vascularPeriferico: [''], neurologico: [''],
        }),
      }),
      diagnosticos: this.fb.array([]),
      tratamientos: this.fb.array([]),
      firma: this.fb.group({ medico: [''], colegiatura: [''], fecha: [''] }),
    });
    this.hcForm.valueChanges
    .pipe(debounceTime(150))
    .subscribe(val => {
      this.ai.evaluate(val);  // 👈 recalcular progreso/faltantes/sugerencias
    });

    this.ai.evaluate(this.hcForm.getRawValue());

    // 2) Conectar a IA (solo navegador)
    if (this.isBrowser) {
      this.sessionId = globalThis.crypto?.randomUUID?.() || String(Date.now());
      this.ai.connect(this.sessionId);
    }

    // 3) Suscripciones STT
    this.subs.push(
      this.wspeech.result$.subscribe((msg: WSPartial) => {
        if (msg.is_final) {
          this.finalText += (msg.text || '').trim() + '. ';
          this.partialText = '';
          if (this.isBrowser) this.ai.sendFinal(msg.text || '');
        } else {
          this.partialText = msg.text || '';
          if (this.isBrowser) this.ai.sendPartial(msg.text || '');
        }
      }),
      this.wspeech.listening$.subscribe(v => (this.listening = v)),
      this.wspeech.level$.subscribe(v => (this.level = v)),
      this.wspeech.error$.subscribe(err => console.warn('[WebSpeech] error:', err))
    );

    // 4) Suscripciones IA (solo navegador)
    if (this.isBrowser) {
      this.subs.push(
        // OJO: si tu servicio se llama assistantText$, cambia esta línea
        this.ai.aiText$.subscribe(t => (this.assistantLive = t || '')),
        this.ai.missing$.subscribe(m => (this.missing = m || [])),
        this.ai.suggestions$.subscribe(s => (this.suggestions = s || [])),
        this.ai.form$.subscribe(json => { if (json) this.patchFormFromAI(json); this.ai.evaluate(this.hcForm.getRawValue());}),
        this.ai.deltas$.subscribe(changes => {
          (changes || []).forEach(ch => {
            const { title, icon } = this.mapPathToTitle(ch.path);
            const desc = ch.reason?.trim() ? ch.reason : `Actualicé ${ch.path}`;
            this.deltaFeed.unshift({ icon, title, desc, path: ch.path, evidence: ch.evidence });
            this.flashControl(ch.path);
          });
        }),
        this.ai.insights$.subscribe(info => {
          if (info) this.deltaFeed.unshift({ icon: '💡', title: info.label, desc: info.text, path: '', evidence: '' });
        }),
      );
    }
  }

  // ---------- Helpers Reactive ----------
  get dxArr(): FormArray { return this.hcForm.get('diagnosticos') as FormArray; }
  get ttoArr(): FormArray { return this.hcForm.get('tratamientos') as FormArray; }

  // ---------- Métodos para Tabs ----------
  setActiveTab(tabId: string) {
    this.activeTab = tabId;
  }

  /** Cuenta campos completados en una sección */
  getCompletedFieldsCount(section: string): number {
    const group = this.hcForm.get(section);
    if (!group) return 0;

    // Para secciones que son FormArrays directamente (diagnosticos, tratamientos)
    if (group instanceof FormArray) {
      return group.length; // número de items agregados
    }

    let completed = 0;

    const countFields = (ctrl: any): void => {
      if (ctrl instanceof FormGroup) {
        Object.keys(ctrl.controls).forEach(key => countFields(ctrl.get(key)));
      } else if (ctrl instanceof FormArray) {
        // Arrays anidados: contar si tienen elementos
        if (ctrl.length > 0) completed++;
      } else if (ctrl instanceof FormControl) {
        const val = ctrl.value;
        if (val !== null && val !== undefined && val !== '') completed++;
      }
    };

    countFields(group);
    return completed;
  }

  /** Cuenta total de campos en una sección */
  getTotalFieldsCount(section: string): number {
    const group = this.hcForm.get(section);
    if (!group) return 0;

    // Para secciones que son FormArrays directamente (diagnosticos, tratamientos)
    if (group instanceof FormArray) {
      // Si está vacío, mostrar "—" o similar, retornar 0 para que el badge muestre "X/—"
      return group.length > 0 ? group.length : 0;
    }

    let total = 0;

    const countFields = (ctrl: any): void => {
      if (ctrl instanceof FormGroup) {
        Object.keys(ctrl.controls).forEach(key => countFields(ctrl.get(key)));
      } else if (ctrl instanceof FormArray) {
        total++;
      } else if (ctrl instanceof FormControl) {
        total++;
      }
    };

    countFields(group);
    return total;
  }

  addDiagnostico(item?: any) {
    this.dxArr.push(this.fb.group({
      nombre: [item?.nombre || '', Validators.required],
      tipo:   [item?.tipo   || ''],
      cie10:  [item?.cie10  || ''],
    }));
  }

  addTratamiento(item?: any) {
    this.ttoArr.push(this.fb.group({
      medicamento:    [item?.medicamento    || '', Validators.required],
      dosisIndicacion:[item?.dosisIndicacion|| ''],
      gtin:           [item?.gtin           || ''],
    }));
  }

  private setStringArray(ctrl: FormArray, data?: string[]) {
    ctrl.clear();
    (data || []).forEach(s => ctrl.push(new FormControl(s)));
  }

  // Patch seguro desde el JSON de la IA (parcial: solo lo que llega)
  private patchFormFromAI(json: HistoriaClinica) {
    if (json.afiliacion) (this.hcForm.get('afiliacion') as FormGroup).patchValue(json.afiliacion, { emitEvent: false });

    if (json.anamnesis) {
      const ana = this.hcForm.get('anamnesis') as FormGroup;
      ana.patchValue({
        tiempoEnfermedad: json.anamnesis.tiempoEnfermedad ?? undefined,
        relato: json.anamnesis.relato ?? undefined,
        funcionesBiologicas: json.anamnesis.funcionesBiologicas ?? undefined,
      }, { emitEvent: false });

      this.setStringArray(ana.get('sintomasPrincipales') as FormArray, json.anamnesis.sintomasPrincipales);
      const ant = ana.get('antecedentes') as FormGroup;
      this.setStringArray(ant.get('personales') as FormArray, json.anamnesis.antecedentes?.personales);
      this.setStringArray(ant.get('padre') as FormArray, json.anamnesis.antecedentes?.padre);
      this.setStringArray(ant.get('madre') as FormArray, json.anamnesis.antecedentes?.madre);
      this.setStringArray(ana.get('alergias') as FormArray, json.anamnesis.alergias);
      this.setStringArray(ana.get('medicamentos') as FormArray, json.anamnesis.medicamentos);
    }

    if (json.examenClinico) (this.hcForm.get('examenClinico') as FormGroup).patchValue(json.examenClinico, { emitEvent: false });

    if (json.diagnosticos) {
      this.dxArr.clear();
      json.diagnosticos.forEach(d => this.addDiagnostico(d));
    }

    if (json.tratamientos) {
      this.ttoArr.clear();
      json.tratamientos.forEach(t => this.addTratamiento(t));
    }

    if (json.firma) (this.hcForm.get('firma') as FormGroup).patchValue(json.firma, { emitEvent: false });
  }

  // ---------- Controles UI ----------
  startMic(): void {
    if (!this.wspeech.supported) {
      alert('Este navegador no soporta Web Speech API. Prueba Chrome/Edge.');
      return;
    }
    this.wspeech.start('es-PE', true, true, true);
  }
  stopMic(): void { this.wspeech.stop(); }

  clearText(): void {
    this.partialText = '';
    this.finalText = '';
    this.hcForm.reset();
    this.dxArr.clear();
    this.ttoArr.clear();
  }

  downloadTxt() {
    const content = (this.finalText || '').trim();
    const blob = new Blob([content + '\n'], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcripcion_${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ---------- Flash de controles ----------
  private flashControl(path: string) {
    const id = this.pathToElementId(path);
    if (!id) return;
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('flash-fill');
    void el.offsetWidth;  // reflow
    el.classList.add('flash-fill');
  }

  private pathToElementId(path: string): string | null {
    const map: Record<string,string> = {
      'afiliacion.motivoConsulta': 'ctrl-motivo',
      'anamnesis.sintomasPrincipales': 'ctrl-sintomas',
      'examenClinico.signosVitales.PA': 'ctrl-pa',
      'examenClinico.signosVitales.temperatura': 'ctrl-temp',
    };
    if (map[path]) return map[path];
    const entry = Object.entries(map).find(([k]) => path.startsWith(k));
    return entry?.[1] ?? null;
  }

  ngOnDestroy(): void {
    this.subs.forEach(s => s.unsubscribe());
    this.stopMic();
    if (this.isBrowser) this.ai.close();
  }

  // --------------------------
  //  UTILIDADES DE FORMATO
  // --------------------------

  private textOrDash(v: any): string {
    if (v === null || v === undefined) return '—';
    if (Array.isArray(v)) return v.length ? v.join(', ') : '—';
    const s = String(v).trim();
    return s.length ? s : '—';
  }

  private h1(doc: jsPDF, text: string, y: number): number {
    doc.setFontSize(16);
    doc.setFont('times', 'bold');
    doc.text(text, 14, y);
    return y + 8;
  }

  private h2(doc: jsPDF, text: string, y: number): number {
    doc.setFontSize(12);
    doc.setFont('times', 'bold');
    doc.text(text, 14, y);
    return y + 6;
  }

  private body(doc: jsPDF, text: string, y: number): number {
    doc.setFontSize(11);
    doc.setFont('times', 'normal');
    const split = doc.splitTextToSize(text, 182);
    doc.text(split, 14, y);
    return y + (split.length * 6);
  }

  private fieldLine(doc: jsPDF, label: string, value: any, y: number): number {
    doc.setFontSize(11);
    doc.setFont('times', 'bold');
    const lbl = `${label}: `;
    const lblWidth = doc.getTextWidth(lbl);

    // label
    doc.text(lbl, 14, y);

    // value
    doc.setFont('times', 'normal');
    const split = doc.splitTextToSize(this.textOrDash(value), 182 - lblWidth);
    doc.text(split, 14 + lblWidth, y);

    return y + Math.max(6, split.length * 6);
  }

  private ensurePage(doc: jsPDF, y: number, needed = 20): number {
    if (y > 280 - needed) {
      doc.addPage();
      return 20;
    }
    return y;
  }

  // --------------------------
  //  EXPORTAR A PDF
  // --------------------------
  exportPdf(): void {
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
      };

      const afiliacion = data.afiliacion || {};
      const anamnesis = data.anamnesis || {};
      const funcionesBio = anamnesis.funcionesBiologicas || {};
      const personales = anamnesis.personales || {};
      const examen = data.examenClinico || {};
      const diagnosticos = data.diagnosticos || [];
      const tratamientos = data.tratamientos || [];
      const interconsultas = data.interconsultas || [];
      const examenes = data.examenes || [];

      const doc = new jsPDF({ unit: 'mm', format: 'a4' });
      let y = 18;

      // Encabezado
      doc.setFontSize(18);
      doc.setFont('times', 'bold');
      doc.text('Historia Clínica — Resumen de Consulta', 14, y);
      y += 6;

      doc.setFontSize(10);
      doc.setFont('times', 'normal');
      const ahora = new Date();
      doc.text(`Generado: ${ahora.toLocaleString()}`, 14, y);
      y += 6;

      // (Opcional) Logo de tu clínica:
      // doc.addImage(base64Logo, 'PNG', 160, 10, 35, 12);

      y = this.ensurePage(doc, y, 14);
      y = this.h1(doc, 'Afiliación', y);

      y = this.fieldLine(doc, 'Nombre', afiliacion.nombreCompleto, y);
      const edadTxt = afiliacion.edad != null ? `${afiliacion.edad} años` : '—';
      const mesesTxt = afiliacion.meses != null ? ` / ${afiliacion.meses} meses` : '';
      y = this.fieldLine(doc, 'Edad', `${edadTxt}${mesesTxt}`, y);
      y = this.fieldLine(doc, 'Sexo', afiliacion.sexo, y);
      y = this.fieldLine(doc, 'DNI', afiliacion.dni, y);
      y = this.fieldLine(doc, 'Grupo', afiliacion.grupoSangre, y);
      y = this.fieldLine(doc, 'Fecha/Hora', afiliacion.fechaHora, y);
      y = this.fieldLine(doc, 'Seguro', afiliacion.seguro, y);
      y = this.fieldLine(doc, 'Tipo consulta', afiliacion.tipoConsulta, y);
      y = this.fieldLine(doc, 'N° Seguro', afiliacion.numeroSeguro, y);
      y = this.fieldLine(doc, 'Motivo de consulta', data.motivoConsulta, y);

      y = this.ensurePage(doc, y, 14);
      y = this.h1(doc, 'Anamnesis', y);

      y = this.fieldLine(doc, 'Tiempo de enfermedad', anamnesis.tiempoEnfermedad, y);
      y = this.fieldLine(doc, 'Síntomas principales', anamnesis.sintomasPrincipales, y);
      y = this.fieldLine(doc, 'Relato', anamnesis.relato, y);

      y = this.h2(doc, 'Funciones biológicas', y);
      y = this.fieldLine(doc, 'Apetito', funcionesBio.apetito, y);
      y = this.fieldLine(doc, 'Sed', funcionesBio.sed, y);
      y = this.fieldLine(doc, 'Orina', funcionesBio.orina, y);
      y = this.fieldLine(doc, 'Deposiciones', funcionesBio.deposiciones, y);
      y = this.fieldLine(doc, 'Sueño', funcionesBio.sueno, y);

      y = this.h2(doc, 'Antecedentes / Personales', y);
      y = this.fieldLine(doc, 'Padre', personales.padre, y);
      y = this.fieldLine(doc, 'Madre', personales.madre, y);
      y = this.fieldLine(doc, 'Alergias', anamnesis.alergias, y);
      y = this.fieldLine(doc, 'Medicamentos', anamnesis.medicamentos, y);

      y = this.ensurePage(doc, y, 14);
      y = this.h1(doc, 'Examen Clínico', y);
      // Vitals en tabla
      const vitals: RowInput[] = [[
        this.textOrDash(examen.PA),
        this.textOrDash(examen.FC),
        this.textOrDash(examen.FR),
        this.textOrDash(examen.temperatura),
        this.textOrDash(examen.SpO2),
        this.textOrDash(examen.IMC),
      ]];

      autoTable(doc, {
        head: [['PA', 'FC', 'FR', 'Temp', 'SpO2', 'IMC']],
        body: vitals,
        startY: y,
        theme: 'grid',
        styles: { fontSize: 10 },
        headStyles: { fillColor: [230, 230, 230] },
        margin: { left: 14, right: 14 }
      });

      y = (doc as any).lastAutoTable.finalY + 6;
      y = this.fieldLine(doc, 'Estado general', examen.estadoGeneral, y);
      y = this.fieldLine(doc, 'Descripción general', examen.descripcionGeneral, y);

      // Diagnósticos (CIE-10)
      if (diagnosticos && diagnosticos.length) {
        y = this.ensurePage(doc, y, 18);
        y = this.h1(doc, 'Diagnósticos (CIE-10)', y);
        const bodyDiag: RowInput[] = diagnosticos.map((d: any, i: number) => ([
          String(i + 1),
          this.textOrDash(d.nombre || d.descripcion || d.label),
          this.textOrDash(d.cie10 || d.codigo),
          this.textOrDash(d.tipo)
        ]));
        autoTable(doc, {
          head: [['#', 'Diagnóstico', 'CIE-10', 'Tipo']],
          body: bodyDiag,
          startY: y,
          theme: 'grid',
          styles: { fontSize: 10 },
          headStyles: { fillColor: [230, 230, 230] },
          margin: { left: 14, right: 14 }
        });
        y = (doc as any).lastAutoTable.finalY + 6;
      }

      // Exámenes (CPT)
      if (examenes && examenes.length) {
        y = this.ensurePage(doc, y, 18);
        y = this.h1(doc, 'Exámenes (CPT)', y);
        const bodyEx: RowInput[] = examenes.map((e: any, i: number) => ([
          String(i + 1),
          this.textOrDash(e.nombre || e.descripcion || e.label),
          this.textOrDash(e.cpt || e.codigo),
          this.textOrDash(e.indicaciones)
        ]));
        autoTable(doc, {
          head: [['#', 'Examen', 'CPT', 'Indicaciones']],
          body: bodyEx,
          startY: y,
          theme: 'grid',
          styles: { fontSize: 10 },
          headStyles: { fillColor: [230, 230, 230] },
          margin: { left: 14, right: 14 }
        });
        y = (doc as any).lastAutoTable.finalY + 6;
      }

      // Tratamientos (CPT/medicación)
      if (tratamientos && tratamientos.length) {
        y = this.ensurePage(doc, y, 18);
        y = this.h1(doc, 'Tratamientos', y);
        const bodyTto: RowInput[] = tratamientos.map((t: any, i: number) => ([
          String(i + 1),
          this.textOrDash(t.medicamento || t.nombre || t.label),
          this.textOrDash(t.dosis || t.dosisIndicaciones || t.indicaciones),
          this.textOrDash(t.cpt || t.codigo)
        ]));
        autoTable(doc, {
          head: [['#', 'Medicamento/Procedimiento', 'Dosis/Indicaciones', 'CPT/Código']],
          body: bodyTto,
          startY: y,
          theme: 'grid',
          styles: { fontSize: 10 },
          headStyles: { fillColor: [230, 230, 230] },
          margin: { left: 14, right: 14 }
        });
        y = (doc as any).lastAutoTable.finalY + 6;
      }

      // Interconsultas
      if (interconsultas && interconsultas.length) {
        y = this.ensurePage(doc, y, 18);
        y = this.h1(doc, 'Interconsultas', y);
        const bodyIC: RowInput[] = interconsultas.map((ic: any, i: number) => ([
          String(i + 1),
          this.textOrDash(ic.especialidad || ic.servicio),
          this.textOrDash(ic.motivo || ic.detalle)
        ]));
        autoTable(doc, {
          head: [['#', 'Especialidad', 'Motivo']],
          body: bodyIC,
          startY: y,
          theme: 'grid',
          styles: { fontSize: 10 },
          headStyles: { fillColor: [230, 230, 230] },
          margin: { left: 14, right: 14 }
        });
        y = (doc as any).lastAutoTable.finalY + 6;
      }

      // Observaciones / Sugerencias IA (si las tienes)
      if (data.sugerenciasIA || data.camposFaltantes) {
        y = this.ensurePage(doc, y, 18);
        y = this.h1(doc, 'Validaciones IA', y);
        if (data.sugerenciasIA) {
          y = this.h2(doc, 'Sugerencias', y);
          y = this.body(doc, this.textOrDash(data.sugerenciasIA), y);
        }
        if (data.camposFaltantes) {
          y = this.h2(doc, 'Campos faltantes', y);
          const faltantes = Array.isArray(data.camposFaltantes)
            ? data.camposFaltantes.join(', ')
            : String(data.camposFaltantes);
          y = this.body(doc, this.textOrDash(faltantes), y);
        }
      }

      // Guardar
      const nombre = afiliacion?.nombreCompleto ? afiliacion.nombreCompleto.replace(/\s+/g, '_') : 'Paciente';
      const fecha = new Date().toISOString().slice(0, 10);
      doc.save(`HC_${nombre}_${fecha}.pdf`);

    } catch (err) {
      console.error('Error exportando PDF', err);
      alert('No se pudo exportar el PDF. Revisa la consola para más detalles.');
    }
  }

  // ---------- Document Upload & Extraction ----------
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    this.uploadAndExtractDocument(file);

    // Reset input para permitir subir el mismo archivo de nuevo
    input.value = '';
  }

  private uploadAndExtractDocument(file: File): void {
    if (!this.isBrowser) return;

    // Validar tamaño (máximo 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      alert('El archivo es demasiado grande. Máximo 10MB.');
      return;
    }

    // Validar tipo
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'];
    if (!validTypes.includes(file.type)) {
      alert('Tipo de archivo no soportado. Usa JPG, PNG, GIF, WEBP o PDF.');
      return;
    }

    this.uploading = true;

    // Crear FormData
    const formData = new FormData();
    formData.append('file', file);

    // Enviar al backend
    const apiUrl = `${environment.apiBase}/extract-document`;

    this.http.post<any>(apiUrl, formData).subscribe({
      next: (response) => {
        this.uploading = false;

        if (response.success && response.data) {
          console.log('[UPLOAD] Datos extraídos:', response.data);

          // Aplicar datos al formulario
          this.applyExtractedData(response.data);

          // Guardar datos extraídos para mostrar en la tab Firma
          this.extractedDataPreview = JSON.stringify(response.data, null, 2);

          // Cambiar a la tab Firma para ver los datos
          this.activeTab = 'firma';
        } else {
          console.error('[UPLOAD] Error en respuesta:', response);
          alert('Error al procesar el documento: ' + (response.error || 'Error desconocido'));
        }
      },
      error: (error) => {
        this.uploading = false;
        console.error('[UPLOAD] Error:', error);

        let errorMsg = 'Error al procesar el documento.';
        if (error.error?.error) {
          errorMsg += ' ' + error.error.error;
        } else if (error.message) {
          errorMsg += ' ' + error.message;
        }

        alert(errorMsg);
      }
    });
  }

  private applyExtractedData(data: any): void {
    try {
      // Aplicar usando el mismo método que usa la IA
      this.patchFormFromAI(data);

      // Añadir mensaje al feed
      this.deltaFeed.unshift({
        icon: '📄',
        title: 'Documento cargado',
        desc: 'Se ha importado información desde el documento médico',
        path: '',
        evidence: ''
      });

      // Evaluar el formulario para actualizar contadores
      this.ai.evaluate(this.hcForm.getRawValue());

    } catch (error) {
      console.error('[APPLY-DATA] Error aplicando datos:', error);
      alert('Error al aplicar los datos extraídos al formulario.');
    }
  }

  clearExtractedData(): void {
    this.extractedDataPreview = '';
  }

}
