import { TestBed } from '@angular/core/testing';

import { SttStreamService } from './stt-stream.service';

describe('SttStreamService', () => {
  let service: SttStreamService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SttStreamService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
