
"""
For Hekstra. Grab images and corresponding metadata:

- rayonix
- timetool info (if available)
- rotation stage position (sam_rot)
- ipm3
- wavelength
- distance

"""

import sys
import psana
import numpy as np
import tables

experiment_name = 'xppls5316' #CHANGE ME

run = int(sys.argv[-1])

ds = psana.MPIDataSource('exp=%s:run=%d' % experiment_name, run)
#ds.break_after(120)
smldata = ds.small_data('/reg/d/psdm/xpp/%s/scratch/hdf5/tmp.h5' % experiment_name,
                        gather_interval=8)

# >>> NEW -- duck type in compression
FILTER = tables.Filters(complib='zlib', complevel=5)
f = tables.open_file('/reg/d/psdm/xpp/%s/scratch/hdf5/r%03d.h5' % experiment_name, run, 
                     mode='w', filters=FILTER)
if smldata.master:
    smldata._small_file.file_handle = f
    #smldata.file_handle = f # tjl sayz no
# <<<

sam_rot = psana.Detector('hekstraphi_DB')
tt_edge = psana.Detector('XPP:TIMETOOL:FLTPOS')
tt_famp = psana.Detector('XPP:TIMETOOL:AMPL')
tt_fwhm = psana.Detector('XPP:TIMETOOL:FLTPOSFWHM')

rayonix    = psana.Detector('rayonix')
work_dist  = psana.Detector('XPP:ROB:POS:Z')

ipm3 = psana.Detector('XppSb3_Ipm')

for nevt, evt in enumerate(ds.events()):

    img = rayonix.calib(evt).astype(np.int16)

    if img is None:
        print 'no image!'
        continue

    smldata.event(rayonix        = img,
                  work_dist      = work_dist(evt),
                  rotation_angle = sam_rot(evt),
                  tt_edge        = tt_edge(evt),
                  tt_famp        = tt_famp(evt),
                  tt_fwhm        = tt_fwhm(evt),
                  ipm3           = ipm3.sum(evt))

    if (nevt % 120) == 0:
        print 'Processed %d events' % (nevt + 1)

smldata.save()