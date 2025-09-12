import { TestBed } from '@angular/core/testing';

import { TimaService } from './tima.service';

describe('TimaService', () => {
  let service: TimaService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TimaService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
