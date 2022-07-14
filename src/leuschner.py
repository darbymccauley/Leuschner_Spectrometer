import casperfpga
from hera_corr_f import SnapFengine
import ugradio

import numpy as np
import time 
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.time import Time
from astropy.io import fits


class Fits(object):
    """
    Create the observation FITS file wherein observation data will be
    stored.
    """
    # def __init__(self):
    #     # Bunch of constants

    def make_PrimaryHDU(self, nspec, coords, coord_sys='ga'):
        """
        Make the PrimaryHDU of the FITS file. Serves as the header 
        containing metadata of the system as well as observation 
        attributes.
        
        Inputs:
        - nspec: Number of spectra to collect.
        - coords: Coordinate(s) of the target.
            Format: (l/ra, b/dec)
        - coord_sys: Coordinate system used for ''coords''.
            Default is galactic coordinates. Takes in either galactic 
            ('ga') or equatorial ('eq') coordinate systems.
        Returns:
        - PrimaryHDU information containing the attributes 
        of the observation and spectrometer.
        """
        # Ensure that a proper coordinate system has been supplied
        if coord_sys != 'ga' and coord_sys != 'eq':
            raise ValueError("Invalid coordinate system supplied: " + coord_sys)

        # Set times
        obs_start_unix = time.time() #unix time
        unix_object = Time(obs_start_unix, format='unix', location=(ugradio.leo.lon, ugradio.leo.lat, ugradio.leo.alt)) #unix time Time object
        obs_start_jd = unix_object.jd #convert unix time to julian date

        # Set the coordinates
        if coord_sys == 'ga':
            l, b = coords*u.degree
            c = SkyCoord(l=l, b=b, frame='galactic')
            equatorial = c.fk5
            ra, dec = equatorial.ra, equatorial.dec
        elif coord_sys == 'eq':
            ra, dec = coords*u.degree
            c = SkyCoord(ra, dec)
            galactic = c.galactic
            l, b = galactic.l, galactic.b
        
        # Make PrimaryHDU
        header = fits.Header()

        # Save metadata of the system and spectrometer
        header['NSPEC'] = (nspec, "Number of spectra collected")
        header['FPGFILE'] = (self.fpgfile, "FPGA FPG file")
        header['HOST'] = (self.s.fpga.host, "Host of the FPGA")
        # header['CLK'] = (self.s.fpga.estimate_fpga_clock(), "FPGA clock speed [MHz]")
        # header['ADC'] = (self.adc_rate, "ADC clock speed [Hz]")
        # header['ADC_NAME'] = (self.s.adc.adc.name, "Name of ADC")
        # header['DOWNSAMPLE'] = (self.downsample, "ADC downsampling period")
        # header['SAMPRATE'] = (self.samp_rate, "Downsampled clock speed [Hz]")
        # header['BW'] = (self.bandwidth, "Bandwidth of spectra [Hz]")
        # header['NCHAN'] = (self.nchan, "Number of frequency channels")
        # header['RES'] = (self.resolution, "Frequency resolution [Hz]")
        # header['FFTSHIFT'] = (self.fft_shift, "FFT shifting instructions")
        # header['ACCLEN'] = (self.acc_len, "Number of clock cycles")
        # header['INTTIME'] = (self.int_time, "Integration time of spectra")
        # header['SCALE'] = (self.scale, "Average instead of sum on SNAP")
        # header['PYTHON'] = (PYTHON_VERSION, "Python version")
        # header['SRC'] = (SRC_CODE, "Source code")
        # header['CASPERFPGA'] = (CASPERFPGA_VERSION, "casperfpga code used")
        # header['HERA_CORR_F'] = (HERA_CORR_F_VERSION, "hera_corr_f code used")
        
        # Save observation attributes
        header['L'] = (l.value, "Galactic longitude [deg]")
        header['B'] = (b.value, "Galactic latitude [deg]")
        header['RA'] = (ra.value, "Right Ascension [deg]")
        header['DEC'] = (dec.value, "Declination [deg]")
        header['JD'] = (obs_start_jd, "Julian date of start time")
        header['UNIX'] = (obs_start_unix, "Seconds since epoch")

        primaryhdu = fits.PrimaryHDU(header=header)
        return primaryhdu


    def make_BinTableHDU(self, data_list, corr_data):
        """
        Make BinTableHDU wherein correlator data will be written to.

        Inputs:
        - data_list = empty list in which columns will be appended to.
        - corr_data: Correlation data saved to the FITS file columns.
            (list of numpy arrays)
        Returns:
        - BinTableHDU that contains the correlation data.
        """        
        # Name of data columns 
        data_names = ['auto0_real', 'auto1_real', 'cross_real', 'cross_imag']

        for i in range(len(data_names)):
            data_list.append(fits.Column(name=data_names[i], format='D', array=corr_data[i]))
        
        bintablehdu = fits.BinTableHDU.from_columns(data_list, name='CORR_DATA')
        return bintablehdu

    
    def write_to_fits(self, hdulist, data_list, corr_data, nspec, coords, coord_sys):
        """
        Write to a FITS file.

        Inputs:
        - hdulist: HDUList into which Primary and BinTable HDUs will be written to. 
        - data_list = empty list in which columns will be appended to.
        - corr_data: Correlation data saved to the FITS file columns.
            (list of numpy arrays)
        - nspec: Number of spectra to collect.
        - coords: Coordinate(s) of the target.
            Format: (l/ra, b/dec)
        - coord_sys: Coordinate system used for ''coords''.
            Default is galactic coordinates. Takes in either galactic 
            ('ga') or equatorial ('eq') coordinate systems.
        Returns: HDUList containing Primary and BinTable HDUs.
        """        
        # append Primary and BinTable HDUs
        hdulist.append(self.make_PrimaryHDU(nspec, coords, coord_sys))
        hdulist.append(self.make_BinTableHDU(data_list, corr_data))

        return hdulist

    
    def save_fits(self, filename, hdulist, overwrite=True):
        """
        Save hdulist to a FITS file with specified name.

        Inputs:
        - filename: name of FITS file to be saved.
            (Format: filename='name_given.fits')
        - hdulist: HDUList that contains Primary and BinTable HDUs. 
        Returns:
        - Saved FITS file
        """
        hdulist.writeto(filename, overwrite=overwrite)

        # #Get rid of ImageHDUs
        # indices = []
        # for i in range(len(hdulist)):
        #     if hdulist[i].name == '':
        #         indices.append(i)
        # for i in range(len(indices)):
        #     hdulist.pop(indec=indices[i])

        # Save and close
        hdulist.close()



# Create Spectrometer class
class Spectrometer(object):
    """
    Casperfpga interface to the SNAP spectrometer.
    """

    def __init__(self):
        """
        Create the interface to the SNAP.
        """
        self.host = 'localhost'
        self.fpgfile = 'fpga/ugradio_corrspec_2022-02-22_0905.fpg'
        
        # self.scale = 0
        # # self.adc_rate = 500e6
        # self.downsample = 1<<3
        # self.bandwidth = 250e6
        # self.samp_rate = self.bandwidth*2
        # self.nchan = 1<<13
        # self.resolution = self.bandwidth/self.nchan
        # self.fft_shift = 1<<14
        # self.acc_len = 1<<27
        # self.clock_rate = self.downsample*self.samp_rate # or 10 MHz?
        # self.int_time = self.acc_len/self.clock_rate


        self.fpga = casperfpga.CasperFpga(self.host)
        self.adc = casperfpga.snapadc.SNAPADC(self.fpga) # 10 MHz reference signal default       
        self.s = SnapFengine(self.host, transport='default')
        

    def is_connected(self):
        """
        Check if the SNAP is connected.
        """
        if self.fpga.is_connected():
            return True
        else:
            return False

    def is_running(self):
        """
        Check if the fpga has been programmed and is running.\
        """
        if self.fpga.is_running() and self.s.is_programmed():
            return True
        else:
            return False

        
    def program(self):
        """
        Program the fpga.
        """
        self.fpga.upload_to_ram_and_program(self.fpgfile)
        self.s.fpga.upload_to_ram_and_program(self.fpgfile)
        

    def initialize(self):
        """
        Programs the fpga on the SNAP and initializes the spectrometer.
        """
        print('Starting the spectrometer...')
        
        # Program fpga
        self.check_connection()
        self.check_running()
        
        # Initialize and align ADCs
        print("Aligning and initializing ADCs...")
        try:
            self.s.adc.init()
            self.s.align_adc()
            print("ADCs aligned and initialized.")
        except: ### No bare excepts
            try: # try again (usually works after two attempts)
                self.s.adc.init()
                self.s.align_adc()
                print("ADCs aligned and initialized.")
            except:
                raise IOError("Could not align and initialize ADCs.")
        
        # Initialize other blocks and both correlators
        print("Initializing other blocks, including PFB and both correlators...")
        try:
            self.s.initialize()
        except:
            self.s.pfb.initialize()
            self.s.corr_0.initialize()
            self.s.corr_1.initialize()

        print('Spectrometer is ready.')



    def read_spec(self, filename, nspec, coords, coord_sys='ga'):
        """
        Recieves data from the Leuschner spectrometer and saves it to a
        FITS file. The primary HDU contains information about the
        observation (coordinates, number of spectra collected, time,
        etc.) and spectrometer attributes used. Each set of spectra is
        stored in its own FITS table in the FITS file. The columns in
        each FITS table are ''auto0_real'', ''auto1_real'',
        ''cross_real'', and ''cross_imag''. All columns contain
        double-precision floating-point numbers.

        Inputs:
        - filename: Name of the output FITs file.
        - nspec: Number of spectra to collect.
        - coords: Coordinate(s) of the target.
            Format: (l/ra, b/dec)
        - coord_sys: Coordinate system used for ''coords''.
            Default is galactic coordinates. Takes in either galactic 
            ('ga') or equatorial ('eq') coordinate systems.
        Returns:
        - FITS file with collected spectrometer data.
        """
        # Make HDUList
        hdul = fits.HDUList()

        # Read some number of spectra to a FITS file
        print('Reading', nspec, 'spectra from the SNAP.')
        ninteg = 0
        while ninteg < nspec:
            cols = []
            ### Want to read corrs at the same time
            ### Split function into corr and spec versions  
            auto0 = self.s.corr_0.get_new_corr(0,0)
            auto1 = self.s.corr_1.get_new_corr(1,1)
            auto0_real, auto1_real = auto0.real, auto1.real
            cross = self.s.corr_0.get_new_corr(0,1)
            cross_real, cross_imag = cross.real, cross.imag
            spectra = [auto0_real, auto1_real, cross_real, cross_imag]

            Fits.write_to_fits(hdul, cols, spectra, nspec, coords, coord_sys)
            ninteg += 1
            
        # Save the output file
        Fits.save_fits(filename, hdul)
