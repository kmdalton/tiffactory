
"""
We will use the following naming convention

shot-<rayonix_timestamp>-pump{0,1}-<set_number>-<angle_index>.rx

here angle index is 1,2,3,...
each integer increment corresponds to a delta_phi rotation

the set number corresponds to the shot index at that fixed angle
"""

import sys
import os
import struct
import h5py
import numpy as np
import argparse


LITTLE_ENDIAN = 1234
BIG_ENDIAN = 4321

def getRxHeader():
    rxfile = open('/reg/d/psdm/xpp/xpplq9215/results/pickle_to_rx/reference.rx.tiff','rb')
    header=rxfile.read(4096)
    return header

def push_data(source,form,offset,index,typelen,value):
    begin = source[0:offset+index]
    end = source[offset+index+typelen:]
    newtext = struct.pack(form,value)
    return begin+newtext+end

def tiff_byte_order_from_string(raw):
    four_bytes = raw[0:4]

    if 'II' in four_bytes[:2]:
        assert(struct.unpack('<H', four_bytes[2:])[0] == 42)
        return LITTLE_ENDIAN
    elif 'MM' in four_bytes[:2]:
        assert(struct.unpack('>H', four_bytes[2:])[0] == 42)
        return BIG_ENDIAN

    raise RuntimeError, '%s not recognised as TIFF' % filename

def modify_basic_image_size(tiff_header,newwidth,newheight):
    # basically an adaptation from dxtbx format FormatTIFFHelpers
    byte_order = tiff_byte_order_from_string(tiff_header)

    if byte_order == LITTLE_ENDIAN:
      _I = '<I'
      _H = '<H'
    else:
      _I = '>I'
      _H = '>H'

    offset = struct.unpack(_I, tiff_header[4:8])[0]

    ntags = struct.unpack(_H, tiff_header[offset:offset + 2])[0]
    start = offset + 2
    for j in range(ntags):
      type_desc = struct.unpack(_H, tiff_header[start:start + 2])[0]
      start += 2
      type_type = struct.unpack(_H, tiff_header[start:start + 2])[0]
      start += 2
      type_size = struct.unpack(_I, tiff_header[start:start + 4])[0]
      start += 4
      if type_type == 4:
        type_offset_or_value = struct.unpack(
            _I, tiff_header[start:start + 4])[0]
        start += 4
      elif type_type == 3:
        type_offset_or_value = struct.unpack(
            _H, tiff_header[start:start + 2])[0]
        start += 4

      if type_desc == 256:
        image_width = type_offset_or_value
        #print "start for image_width is ",start-4,type_type,type_size,_I,image_width
        w_index = start-4
        w_form = _I
        w_len = {4:4,3:2}[type_type]
    
      elif type_desc == 257:
        image_height = type_offset_or_value
        #print "start for image_height is ",start-4,type_type,type_size,_I,image_height
        h_index = start-4
        h_form = _I
        h_len = {4:4,3:2}[type_type]

      elif type_desc == 258:
        image_depth = type_offset_or_value
      elif type_desc == 273:
        header_size = type_offset_or_value

    #now comes the modification:
    newdata = push_data(tiff_header,w_form,offset=0,index=w_index,typelen=w_len,value=newwidth)
    newdata = push_data(newdata,h_form,offset=0,index=h_index,typelen=h_len,value=newheight)
    return newdata

def write_tiff_detail(d, path, delta_phi, angle_index):
  #assure that the 2-byte data are within the unsigned limits
  #selecthi = d["DATA"]>65535
  #d["DATA"].set_selected(selecthi,0)
  #selectlo = d["DATA"]<0
  #d["DATA"].set_selected(selectlo,0)

  #idata = d["DATA"].as_numpy_array()
  #idata =  idata.astype("uint16")
  idata = d["DATA"].astype("uint16")
  string_data = idata.tostring()

  raw_header = getRxHeader()
  offset=1024
  new_header = push_data(raw_header,form="<I",offset=offset,index=80,typelen=4,value=d["SIZE1"])
  new_header = push_data(new_header,form="<I",offset=offset,index=84,typelen=4,value=d["SIZE2"])
  new_header = modify_basic_image_size(new_header,d["SIZE1"],d["SIZE2"])

  beamx_px_1000 = int(1000*d["SIZE1"]*d["PIXEL_SIZE"]/2.)
  beamy_px_1000 = int(1000*d["SIZE2"]*d["PIXEL_SIZE"]/2.)
  new_header = push_data(new_header,form="<I",offset=offset,index=644,typelen=4,value=beamx_px_1000)
  new_header = push_data(new_header,form="<I",offset=offset,index=648,typelen=4,value=beamy_px_1000)

  px_sz_nm = int(1000000 * d["PIXEL_SIZE"])
  new_header = push_data(new_header,form="<I",offset=offset,index=772,typelen=4,value=px_sz_nm)
  new_header = push_data(new_header,form="<I",offset=offset,index=776,typelen=4,value=px_sz_nm)

  distance_1000 = int(1000 * d["DISTANCE"])
  new_header = push_data(new_header,form="<I",offset=offset,index=696,typelen=4,value=distance_1000)
  new_header = push_data(new_header,form="<I",offset=offset,index=640,typelen=4,value=distance_1000)

  wave_fm = int(d["WAVELENGTH"] * 100000)
  new_header = push_data(new_header,form="<I",offset=offset,index=908,typelen=4,value=wave_fm)

  start_phi=int(1000* (angle_index-1)*delta_phi)
  end_phi=int(1000* (angle_index)*delta_phi)
  new_header = push_data(new_header,form="<I",offset=offset,index=684,typelen=4,value=start_phi)
  new_header = push_data(new_header,form="<I",offset=offset,index=716,typelen=4,value=end_phi)
  new_header = push_data(new_header,form="<I",offset=offset,index=732,typelen=4,value=4) # rotation axis
  new_header = push_data(new_header,form="<I",offset=offset,index=736,typelen=4,value=int(1000*delta_phi))

  nheaders = struct.unpack("<I",new_header[76+offset:80+offset])[0]
  nfast = struct.unpack("<I",new_header[80+offset:84+offset])[0]
  nslow = struct.unpack("<I",new_header[84+offset:88+offset])[0]

  image_data = new_header + string_data

  file(path,"wb").write(image_data)
  return


def write_tiff(file_handle, index, path, delta_phi, rot):

    hc = 1.2398e4
    img = file_handle['rayonix'][index]
    l = hc / file_handle['ebeam/photon_energy'][index]

    d = {'SIZE1' :      img.shape[0],
         'SIZE2' :      img.shape[1],
         'DISTANCE' :   file_handle['work_dist'][index],
         'PIXEL_SIZE' : 0.089,
         'WAVELENGTH' : l,
         'DATA'       : img
        }

    write_tiff_detail(d, path, delta_phi, rot)
    print path

    return


def get_brightest(runs, target_path):


    print '*'*50
    print ''
    print 'PROCESSING RUNS: %s' % str(runs)
    print '--> %s' % target_path

    os.system('mkdir -p %s' % target_path)
    os.system('mkdir %s/on' % target_path)
    os.system('mkdir %s/off' % target_path)

    last_rot_index = 0
    for r in runs:

        hdf5_path = '/reg/d/psdm/xpp/xpplq9215/scratch/hdf5/r%03d.h5' % int(r)
        print '> reading: %s' % hdf5_path
        f = h5py.File(hdf5_path, 'r')

        readout = np.array(f['evr/code_95']) * np.array(f['evr/code_97'])
        pumped  = np.array(f['evr/code_90'])
        ipm3    = np.array(f['ipm3'])

        rotation  = np.array(f['rotation_angle'])
        delta_phi = 0.25

        rotation_index = np.abs( np.round(((rotation - rotation[1]) / delta_phi)).astype(np.int) ) + last_rot_index + 1

        for rot in np.unique(rotation_index[1:]):

            best_off = np.argmax( (rotation_index == rot) * (pumped == 0) * readout * ipm3 )
            best_on  = np.argmax( (rotation_index == rot) * (pumped == 1) * readout * ipm3 )

            write_tiff(f, best_off, '%s/off/x_%05d.tiff' % (target_path, rot), delta_phi, rot)
            write_tiff(f, best_on,  '%s/on/x_%05d.tiff' % (target_path, rot), delta_phi, rot)

        f.close()
        last_rot_index = rotation_index[-1]

    return


def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', type=int, nargs='+', help='runs to process')
    parser.add_argument('target_dir', type=str, help='place to save tiffs')    
    args = parser.parse_args()

    get_brightest(args.runs, args.target_dir)

    return


if __name__ == '__main__':
    main()


