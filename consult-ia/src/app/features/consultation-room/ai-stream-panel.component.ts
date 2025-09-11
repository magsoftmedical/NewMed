import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { AiStreamState, FilledField } from '../../core/ai-stream.state';

@Component({
  selector: 'ai-stream-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ai-stream-panel.component.html',
  styleUrls: ['./ai-stream-panel.component.scss']
})
export class AiStreamPanelComponent implements OnInit, OnDestroy {
  private sub?: Subscription;

  fields: FilledField[] = [];
  sections: string[] = [];
  open: string | null = null;

  constructor(public state: AiStreamState) {}

  ngOnInit(): void {
    this.sub = this.state.list$.subscribe((list: FilledField[]) => {
      this.fields = list;
      this.sections = [...new Set(list.map(x => x.section))];
      if (!this.open && this.sections.length) this.open = this.sections[0];
    });
  }
  ngOnDestroy(): void { this.sub?.unsubscribe(); }

  bySection(s: string)  { return this.fields.filter(f => f.section === s); }
  completed()           { return this.fields.filter(f => f.value !== undefined && f.value !== '').length; }
  total()               { return this.fields.length; }
  completedIn(s: string){ return this.bySection(s).filter(f => f.value !== undefined && f.value !== '').length; }
  progress()            { const t = this.total(); return t ? (this.completed() / t) * 100 : 0; }
  trackByPath(_: number, f: FilledField){ return f.path; }
  toggle(s: string)     { this.open = this.open === s ? null : s; }

  clearField(f: FilledField){ this.state.applyDelta({ path: f.path, value: '' }); }
  clearAll(){ this.state.clearAll(); }
}
