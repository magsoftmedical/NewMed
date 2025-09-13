import { Routes } from '@angular/router';
import { ConsultationRoomComponent } from './features/consultation-room/consultation-room.component';

export const routes: Routes = [
  { path: '', redirectTo: 'consult', pathMatch: 'full' },
  { path: 'consult', component: ConsultationRoomComponent },
  // otras rutas que tengas…
  { path: '**', redirectTo: 'consult' },
];
