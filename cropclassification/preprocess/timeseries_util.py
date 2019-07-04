# -*- coding: utf-8 -*-
"""
Calculates periodic timeseries for input parcels.
"""

from datetime import datetime
import logging
import glob
import os

import geopandas as gpd
import numpy as np
import pandas as pd

# Import local stuff
import cropclassification.helpers.config_helper as conf
import cropclassification.helpers.geofile as geofile_util
import cropclassification.helpers.pandas_helper as pdh

#-------------------------------------------------------------
# First define/init some general variables/constants
#-------------------------------------------------------------
# Get a logger...
logger = logging.getLogger(__name__)

IMAGETYPE_S1_GRD = 'S1_GRD'
IMAGETYPE_S1_COHERENCE = 'S1_COH'
IMAGETYPE_S2_L2A = 'S2_L2A'

def prepare_input(input_parcel_filepath: str,
                  output_imagedata_parcel_input_filepath: str,
                  output_parcel_nogeo_filepath: str = None,
                  force: bool = False):
    """
    This function creates a file that is preprocessed to be a good input file for
    timeseries extraction of sentinel images.

    Args
        input_parcel_filepath: input file
        output_imagedata_parcel_input_filepath: prepared output file
        output_parcel_nogeo_filepath: output file with a copy of the non-geo data
        force: force creation, even if output file(s) exist already

    """
    ##### Check if parameters are OK and init some extra params #####
    if not os.path.exists(input_parcel_filepath):
        raise Exception(f"Input file doesn't exist: {input_parcel_filepath}")
    
    # Check if the input file has a projection specified
    if geofile_util.get_crs(input_parcel_filepath) is None:
        message = f"The parcel input file doesn't have a projection/crs specified, so STOP: {input_parcel_filepath}"
        logger.critical(message)
        raise Exception(message)

    # If force == False Check and the output file exists already, stop.
    if(force is False 
       and os.path.exists(output_imagedata_parcel_input_filepath)
       and (output_parcel_nogeo_filepath is None or os.path.exists(output_parcel_nogeo_filepath))):
        logger.warning("prepare_input: force == False and output files exist, so stop: " 
                       + f"{output_imagedata_parcel_input_filepath}, "
                       + f"{output_parcel_nogeo_filepath}")
        return

    logger.info(f"Process input file {input_parcel_filepath}")

    # Create temp dir to store temporary data for tracebility
    output_dir, output_filename = os.path.split(output_imagedata_parcel_input_filepath)
    output_filename_noext = os.path.splitext(output_filename)[0]
    temp_output_dir = os.path.join(output_dir, 'temp')
    if not os.path.exists(temp_output_dir):
        os.mkdir(temp_output_dir)

    ##### Read the parcel data and write nogeo version #####
    parceldata_gdf = geofile_util.read_file(input_parcel_filepath)
    logger.info(f'Parceldata read, shape: {parceldata_gdf.shape}')

    # Check if the id column is present and set as index
    if conf.columns['id'] in parceldata_gdf.columns:
        parceldata_gdf.set_index(conf.columns['id'], inplace=True)
    else:
        message = f"STOP: Column {conf.columns['id']} not found in input parcel file: {input_parcel_filepath}. Make sure the column is present or change the column name in global_constants.py"
        logger.critical(message)
        raise Exception(message)
        
    if force is True or os.path.exists(output_parcel_nogeo_filepath) == False:
        logger.info(f"Save non-geo data to {output_parcel_nogeo_filepath}")
        parceldata_nogeo_df = parceldata_gdf.drop(['geometry'], axis = 1)
        pdh.to_file(parceldata_nogeo_df, output_parcel_nogeo_filepath)

    ##### Do the necessary conversions and write buffered file #####
    
    # If force == False Check and the output file exists already, stop.
    if(force is False 
       and os.path.exists(output_imagedata_parcel_input_filepath)):
        logger.warning("prepare_input: force == False and output files exist, so stop: " 
                       + f"{output_imagedata_parcel_input_filepath}")
        return

    logger.info('Apply buffer on parcel')
    parceldata_buf_gdf = parceldata_gdf.copy()

    # resolution = number of segments per circle
    buffer_size = -conf.marker.getint('buffer')
    parceldata_buf_gdf[conf.columns['geom']] = (parceldata_buf_gdf[conf.columns['geom']]
                                                .buffer(buffer_size, resolution=5))

    # Export buffered geometries that result in empty geometries
    logger.info('Export parcels that are empty after buffer')
    parceldata_buf_empty_df = parceldata_buf_gdf.loc[
            parceldata_buf_gdf[conf.columns['geom']].is_empty == True]
    if len(parceldata_buf_empty_df.index) > 0:
        parceldata_buf_empty_df.drop(conf.columns['geom'], axis=1, inplace=True)
        temp_empty_filepath = os.path.join(temp_output_dir, f"{output_filename_noext}_empty.sqlite")
        pdh.to_file(parceldata_buf_empty_df, temp_empty_filepath)

    # Export parcels that don't result in a (multi)polygon
    parceldata_buf_notempty_gdf = parceldata_buf_gdf.loc[
            parceldata_buf_gdf[conf.columns['geom']].is_empty == False]
    parceldata_buf_nopoly_gdf = parceldata_buf_notempty_gdf.loc[
            ~parceldata_buf_notempty_gdf[conf.columns['geom']].geom_type.isin(['Polygon', 'MultiPolygon'])]
    if len(parceldata_buf_nopoly_gdf.index) > 0:
        logger.info('Export parcels that are no (multi)polygons after buffer')
        parceldata_buf_nopoly_gdf.drop(conf.columns['geom'], axis=1, inplace=True)      
        temp_nopoly_filepath = os.path.join(temp_output_dir, f"{output_filename_noext}_nopoly.sqlite")
        geofile_util.to_file(parceldata_buf_nopoly_gdf, temp_nopoly_filepath)

    # Export parcels that are (multi)polygons after buffering
    parceldata_buf_poly_gdf = parceldata_buf_notempty_gdf.loc[
            parceldata_buf_notempty_gdf[conf.columns['geom']].geom_type.isin(['Polygon', 'MultiPolygon'])]
    for column in parceldata_buf_poly_gdf.columns:
        if column not in [conf.columns['id'], conf.columns['geom']]:
            parceldata_buf_poly_gdf.drop(column, axis=1, inplace=True)
    logger.info(f"Export parcels that are (multi)polygons after buffer to {output_imagedata_parcel_input_filepath}")
    geofile_util.to_file(parceldata_buf_poly_gdf, output_imagedata_parcel_input_filepath)
    logger.info(parceldata_buf_poly_gdf)

def calculate_periodic_data(
            input_parcel_filepath: str,
            input_base_dir: str,
            start_date_str: str,   
            end_date_str: str,    
            sensordata_to_get: [],       
            dest_data_dir: str,
            force: bool = False):
    """
    This function creates a file that is a weekly summarize of timeseries images from DIAS.

    TODO: add possibility to choose which values to extract (mean, min, max,...)?
        
    Args:
        input_parcel_filepath (str): [description]
        input_base_dir (str): [description]
        start_date_str (str): Start date in format %Y-%m-%d. Needs to be aligned already on the 
                periods wanted.
        end_date_str (str): End date in format %Y-%m-%d. Needs to be aligned already on the 
                periods wanted.
        sensordata_to_get ([]): 
        dest_data_dir (str): [description]
        force (bool, optional): [description]. Defaults to False.
    """
    logger.info('calculate_periodic_data')

    # Init    
    input_parcels_filename = os.path.basename(input_parcel_filepath)
    input_parcels_filename_noext, _ = os.path.splitext(input_parcels_filename)
    input_dir = os.path.join(input_base_dir, input_parcels_filename_noext)

    # TODO: in config?
    input_ext = ".sqlite"
    output_ext = ".sqlite"

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d') 
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') 
    year = start_date_str.split("-")[0] 

    # Prepare output dir
    test = False
    if test is True:
        dest_data_dir += "_test"
    if not os.path.exists(dest_data_dir):
        os.mkdir(dest_data_dir)
    
    # Create Dataframe with all files with their info
    logger.debug('Create Dataframe with all files and their properties')
    file_info_list = []
    for filename in os.listdir(input_dir): 
        if filename.endswith(input_ext):
            # Get seperate filename parts
            file_info = get_file_info(os.path.join(input_dir, filename))
            file_info_list.append(file_info)
    
    all_inputfiles_df = pd.DataFrame(file_info_list)

    # Loop over the data we need to get
    id_column = conf.columns['id']
    for sensordata_type in sensordata_to_get:

        logger.debug('Get files we need based on start- & stopdates, sensordata_to_get,...')
        orbits = [None]
        if sensordata_type == conf.general['SENSORDATA_S1_ASCDESC']:
            # Filter files to the ones we need
            satellitetype = 'S1'
            imagetype = IMAGETYPE_S1_GRD
            bands = ['VV', 'VH']
            orbits = ['ASC', 'DESC']
            needed_inputfiles_df = all_inputfiles_df.loc[(all_inputfiles_df.date >= start_date) 
                                                         & (all_inputfiles_df.date < end_date)
                                                         & (all_inputfiles_df.imagetype == imagetype)
                                                         & (all_inputfiles_df.band.isin(bands))
                                                         & (all_inputfiles_df.orbit.isin(orbits))]
        elif sensordata_type == conf.general['SENSORDATA_S2gt95']:
            satellitetype = 'S2'
            imagetype = IMAGETYPE_S2_L2A
            bands = ['B02-10m', 'B03-10m', 'B04-10m', 'B08-10m']
            needed_inputfiles_df = all_inputfiles_df.loc[(all_inputfiles_df.date >= start_date) 
                                                         & (all_inputfiles_df.date < end_date) 
                                                         & (all_inputfiles_df.imagetype == imagetype)                                                         
                                                         & (all_inputfiles_df.band.isin(bands))]
        elif sensordata_type == conf.general['SENSORDATA_S1_COHERENCE']:
            satellitetype = 'S1'
            imagetype = IMAGETYPE_S1_COHERENCE
            bands = ['VV', 'VH']
            orbits = ['ASC', 'DESC']
            needed_inputfiles_df = all_inputfiles_df.loc[(all_inputfiles_df.date >= start_date) 
                                                         & (all_inputfiles_df.date < end_date) 
                                                         & (all_inputfiles_df.imagetype == imagetype)                                                         
                                                         & (all_inputfiles_df.band.isin(bands))]
        else:
            raise Exception(f"Unsupported sensordata_type: {sensordata_type}")

        # There should also be one pixcount file
        pixcount_filename = f"{input_parcels_filename_noext}_weekly_pixcount{output_ext}"
        pixcount_filepath = os.path.join(dest_data_dir, pixcount_filename)

        # For each week
        start_week = int(datetime.strftime(start_date , '%W'))
        end_week = int(datetime.strftime(end_date , '%W'))
        for period_index in range(start_week, end_week):

            # Get the date of the first day of period period_index (eg. monday for a week)
            period_date = datetime.strptime(str(year) + '_' + str(period_index) + '_1', '%Y_%W_%w')

            # New file name
            period_date_str_long = period_date.strftime('%Y-%m-%d') 
            period_data_filename = f"{input_parcels_filename_noext}_weekly_{period_date_str_long}_{sensordata_type}{output_ext}"
            period_data_filepath = os.path.join(dest_data_dir, period_data_filename)

            # Check if output file exists already
            if os.path.exists(period_data_filepath):
                if force is False:
                    logger.info(f"SKIP: force is False and file exists: {period_data_filepath}")
                    continue
                else:
                    os.remove(period_data_filepath)

            # Loop over bands and orbits (all combinations of bands and orbits!)
            logger.info(f"Calculate file: {period_data_filename}")
            period_data_df = None
            for band, orbit in [(band, orbit) for band in bands for orbit in orbits]:

                # Get list of files needed for this period, band
                period_files_df = needed_inputfiles_df.loc[(needed_inputfiles_df.week == period_index)
                                                           & (needed_inputfiles_df.band == band)]
                
                # If an orbit to be filtered was specified, filter
                if orbit is not None:
                    period_files_df = period_files_df.loc[(period_files_df.orbit == orbit)]

                # Loop all period_files
                period_band_data_df = None
                statistic_columns_dict = {'count': [], 'max': [], 'mean': [], 'min': [], 'std': []}
                for j, imagedata_filepath in enumerate(period_files_df.filepath.tolist()):
                    
                    # If file has filesize == 0, skip
                    if os.path.getsize(imagedata_filepath) == 0:
                        continue 

                    # Read the file (but only the columns we need)
                    columns = [column for column in statistic_columns_dict].append(id_column)
                    image_data_df = pdh.read_file(imagedata_filepath, columns=columns)
                    image_data_df.set_index(id_column, inplace=True)
                    image_data_df.index.name = id_column

                    # Rename columns so column names stay unique
                    for statistic_column in statistic_columns_dict:
                        new_column_name = statistic_column + str(j+1)
                        image_data_df.rename(columns={statistic_column: new_column_name},
                                             inplace=True)
                        statistic_columns_dict[statistic_column].append(new_column_name)
                                            
                    # Create 1 dataframe for all weekfiles - one row for each code_obj - using concat (code_obj = index)
                    if period_band_data_df is None:
                        period_band_data_df = image_data_df                
                    else:
                        period_band_data_df = pd.concat([period_band_data_df, image_data_df], axis=1, sort=False)
                        # Apparently concat removes the index name in some situations
                        period_band_data_df.index.name = id_column
                        
                # Calculate max, mean, min, ...
                if period_band_data_df is not None:
                    logger.debug('Calculate max, mean, min, ...')
                    period_date_str_short = period_date.strftime('%Y%m%d')
                    # Remark: prefix column names: sqlite doesn't like a numeric start
                    if orbit is None:
                        column_basename = f"TS_{period_date_str_short}_{imagetype}_{band}"
                    else:
                        column_basename = f"TS_{period_date_str_short}_{imagetype}_{orbit}_{band}"

                    # Number of pixels
                    # TODO: onderzoeken hoe aantal pixels best bijgehouden wordt : afwijkingen weglaten ? max nemen ? ...
                    period_band_data_df[f"{column_basename}_count"] = np.nanmax(period_band_data_df[statistic_columns_dict['count']], axis=1)
                    # Maximum of all max columns
                    period_band_data_df[f"{column_basename}_max"] = np.nanmax(period_band_data_df[statistic_columns_dict['max']], axis=1)
                    # Mean of all mean columns
                    period_band_data_df[f"{column_basename}_mean"] = np.nanmean(period_band_data_df[statistic_columns_dict['mean']], axis=1)
                    # Minimum of all min columns
                    period_band_data_df[f"{column_basename}_min"] = np.nanmin(period_band_data_df[statistic_columns_dict['min']], axis=1)
                    # Mean of all std columns
                    period_band_data_df[f"{column_basename}_std"] = np.nanmean(period_band_data_df[statistic_columns_dict['std']], axis=1)
                    # Number of Files used
                    period_band_data_df[f"{column_basename}_used_files"] = period_band_data_df[statistic_columns_dict['max']].count(axis=1)
                                    
                    # Only keep the columns we want to keep
                    columns_to_keep = [f"{column_basename}_count", f"{column_basename}_max", 
                                    f"{column_basename}_mean", f"{column_basename}_min", 
                                    f"{column_basename}_std", f"{column_basename}_used_files"] 
                    period_band_data_df = period_band_data_df[columns_to_keep]

                    # Merge the data with the other bands/orbits for this period
                    if period_data_df is None:
                        period_data_df = period_band_data_df
                    else:
                        period_data_df = pd.concat([period_band_data_df, period_data_df], axis=1, sort=False) 
                        # Apparently concat removes the index name in some situations
                        period_data_df.index.name = id_column
            
            if period_data_df is not None:
                logger.info(f"Write new file: {period_data_filename}")
                pdh.to_file(period_data_df, period_data_filepath)

                if not os.path.exists(pixcount_filepath):
                    pixcount_s1s2_column = conf.columns['pixcount_s1s2']
                    for column in period_data_df.columns:
                        if column.endswith('_count'):
                            period_data_df.rename(columns={column: pixcount_s1s2_column}, inplace=True)
                            break
                    pixcount_df = period_data_df[pixcount_s1s2_column]
                    pixcount_df.fillna(value=0, inplace=True)
                    pdh.to_file(pixcount_df, pixcount_filepath)

def get_file_info(filepath: str) -> dict:
    """
    This function gets info of a timeseries data file.
    
    Args:
        filepath (str): The filepath to the file to get info about.
        
    Returns:
        dict: a dict containing info about the file
    """

    try:
        # Remove extension
        filename = os.path.splitext(filepath)[0] 

        # Split name on parcelinfo versus imageinfo
        filename_splitted = filename.split("__")
        filename_parcelinfo = filename_splitted[0]
        filename_imageinfo = filename_splitted[1]

        # Extract imageinfo
        imageinfo_values = filename_imageinfo.split("_")    

        # Satellite 
        satellite = imageinfo_values[0]

        # Get the date taken from the filename, depending on the satellite type
        # Remark: the datetime is in this format: '20180101T055812'
        if satellite.startswith('S1'):
            # Check if it is a GRDH image
            if imageinfo_values[2] == 'GRDH':
                imagetype = IMAGETYPE_S1_GRD
                filedatetime = imageinfo_values[4]  
            elif imageinfo_values[1].startswith('S1'):
                imagetype = IMAGETYPE_S1_COHERENCE
                filedatetime = imageinfo_values[2]  
        elif satellite.startswith('S2'):
            imagetype = IMAGETYPE_S2_L2A
            filedatetime = imageinfo_values[2]  

        filedate = filedatetime.split("T")[0]  
        parseddate = datetime.strptime(filedate, '%Y%m%d') 
        fileweek = int(parseddate.strftime('%W'))

        # Get the band 
        fileband = imageinfo_values[-1]         # =last value

        # For S1 images, get the orbit 
        if satellite.startswith('S1'):
            fileorbit = imageinfo_values[-2]    # =2nd last value
        else:
            fileorbit = None

        filenameparts = {
            'filepath': filepath,
            'imagetype': imagetype,
            'filename' : filename,
            'date' : parseddate,
            'week' : fileweek,
            'band' : fileband, 
            'orbit' : fileorbit} # ASC/DESC

    except Exception as ex:
        message = f"Error extracting info from filename {filepath}"
        logger.exception(message)
        raise Exception(message) from ex

    return filenameparts


def get_monday(input_date):
    """
    This function gets the first monday before the date provided.
    She is being used to adapt start_date and end_date so they are mondays, so it becomes easier to reuse timeseries data
      Inputformaat: %Y-%m-%d
      outputformaat: %Y_%W_%w vb 2018_5_1 -  2018 - week 5 - monday.
    """
    parseddate = datetime.strptime(input_date, '%Y-%m-%d')
    year_week = parseddate.strftime('%Y_%W')
    year_week_monday = datetime.strptime(year_week + '_1', '%Y_%W_%w') 
    return year_week_monday

# If the script is run directly...
if __name__ == "__main__":
    raise Exception("Not implemented")
    