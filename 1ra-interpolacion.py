# -*- coding: utf-8 -*-
"""
Created on Thu Mar 23 18:35:30 2023

@author: Jerónimo García
"""

import numpy as np
import pandas as pd
from scipy.interpolate import griddata
from datetime import datetime, date, timedelta
from netCDF4 import num2date, date2num, Dataset as NetCDFFile

input_file = 'carra-files/param_130.nc'
nc = NetCDFFile(input_file)

longitudes = nc.variables['longitude'][100:475, 477:]
latitudes = nc.variables['latitude'][100:475, 477:]
raw_times = nc.variables['time'][:]
temperture = nc.variables['t'][..., 100:475, 477:]
#wind_direction = nc.variables['u'][..., 100:500, 450:]
#wind_speed = nc.variables['v'][..., 100:500, 450:]
nc.close()

new_longitudes = np.where(longitudes <= 180, longitudes, longitudes - 360)

reshaped_longitudes = new_longitudes.view().reshape(np.size(longitudes), 1)
reshaped_latitudes = latitudes.view().reshape(np.size(latitudes), 1)
coords_full_set = np.hstack((reshaped_longitudes, reshaped_latitudes))
    
longitudes_to_interp = np.linspace(25.5, 25, 72).reshape(72, 1)
latitudes_to_interp = np.linspace(66, 69, 72).reshape(72, 1)
coords_to_interp = np.block([longitudes_to_interp, latitudes_to_interp])


arc_files = ["explotion-times/2016-231_12.29.58.500.ARC", "explotion-times/2016-232_11.29.59.350.ARC", 
             "explotion-times/2016-233_13.29.59.550.ARC", "explotion-times/2016-234_13.00.00.100.ARC", 
             "explotion-times/2016-235_11.59.59.500.ARC", "explotion-times/2016-236_12.59.59.450.ARC", 
             "explotion-times/2016-237_11.59.59.400.ARC", "explotion-times/2016-238_11.29.59.400.ARC", 
             "explotion-times/2016-239_11.29.58.650.ARC", "explotion-times/2016-240_12.59.59.100.ARC", 
             "explotion-times/2016-241_10.59.59.000.ARC", "explotion-times/2016-242_09.59.58.550.ARC", 
             "explotion-times/2016-242_14.09.58.450.ARC", "explotion-times/2016-243_07.54.57.750.ARC", 
             "explotion-times/2016-243_10.04.57.300.ARC", "explotion-times/2016-243_12.24.56.850.ARC", 
             "explotion-times/2016-244_08.49.58.950.ARC", "explotion-times/2016-244_11.44.58.700.ARC",
             "explotion-times/2016-244_15.44.58.750.ARC"]

whole_dates = np.array([datetime.utcfromtimestamp(posix_timestamp).strftime('%Y-%m-%dT%H:%M') for posix_timestamp in raw_times], dtype='datetime64[m]')

explosion_dates = np.empty(len(arc_files), dtype='datetime64[m]')
for index, file in enumerate(arc_files):
    data = pd.read_csv(file,delim_whitespace=True,header=None)
    
    explotion = np.argmax(data.iloc[:,3])
    date_of_explotion = data.iloc[explotion,0]
    year_of_explotion = date_of_explotion[0:4]
    day_number_of_explotion = date_of_explotion[5:8]
    hour_of_explotion = date_of_explotion[9:11]
    minutes_of_explotion = date_of_explotion[12:14]
    
    day_number_of_explotion = day_number_of_explotion.rjust(3 + len(day_number_of_explotion), '0')
    template_date = datetime(int(year_of_explotion), 1, 1, int(hour_of_explotion), int(minutes_of_explotion))
    resulting_object_date = template_date + timedelta(days=int(day_number_of_explotion) - 1)
    resulting_string_date = resulting_object_date.strftime('%Y-%m-%dT%H:%M')
    explosion_dates[index] = resulting_string_date
    
def date_cleaner(whole_dates, explosion_dates):
    
    def index_finder(datetime_array, explosion_date):
        indices = np.argsort(np.abs(datetime_array - explosion_date))[:2]
        return indices
    
    desired_indices = []
    with np.nditer([explosion_dates], flags=['buffered'], op_flags=['readonly']) as it:
        for explosion_date in it:
            desired_indices.extend(index_finder(whole_dates, explosion_date))
            
    return desired_indices
       
desired_indices = np.unique(date_cleaner(whole_dates, explosion_dates))
cleaned_dates = whole_dates[desired_indices]


def request_to_interpolate_again():
    
    user_choice = input('Volver a hacer otra interpolación?\n1. Sí\n2. No\nRespuesta: ')
    
    if ((user_choice.strip().capitalize() in ['Sí', 'Si']) or (user_choice == '1')):
        kind_of_measurement = int(input('1. Temperatura\n2. Velocidd del viento\n3. Dirección del viento\nIntroduce el número de la medida a interpolar: '))
        
        while (kind_of_measurement in range(1, 4)):
            print('\nInterpolación en proceso...\n')
            first_interpolator(kind_of_measurement, cleaned_dates)
            kind_of_measurement = False

    else: 
        print('\nEntendido\n')
    
    """ Aquí posiblemente haya una función que devuelva un archivo csv o txt que almacene los datos de las interpolaciones deseadas. """

def first_interpolator(kind_of_measurement, selected_time, out=None):
    
    def second_interpolator(sequence_of_interpolants):
        
        array_of_interpolants = np.array(sequence_of_interpolants)
        print(np.shape(array_of_interpolants))
        # shape(heigths, times, interpolants)
        index = 0
        with np.nditer([array_of_interpolants, out], flags=['buffered', 'multi_index', 'refs_ok'], op_flags=[['readonly'], ['readonly'], ['writeonly', 'allocate', 'no_broadcast']]) as it: 
            for measurement_values, interpolants_for_a_time in it: 
                interpolant = np.interp(explosion_dates, cleaned_dates.ravel(), [measurement_values[..., index], measurement_values[..., index + 1]]) 
                interpolants_for_a_time[...] = interpolant 
                index += 1
                result= it.operands[1]
        print(result)
    
        print('\nInterpolación temporal exitosa\n')
        return request_to_interpolate_again()
    
    if (kind_of_measurement == 1):
        cleaned_temperture = np.take(temperture, desired_indices, axis=0)
        
        for height in range(23):
            measurements_at_same_height = np.empty(len(cleaned_dates), dtype='object')
            
            for time in range(np.size(cleaned_dates)):
                flatten_temperture = cleaned_temperture[time, height, ...].ravel()
                temperture_interpolants = griddata(coords_full_set, flatten_temperture, coords_to_interp, method='cubic')
                measurements_at_same_height[index] = list(temperture_interpolants)
                
            sequence_of_interpolants.append(measurements_at_same_height)
            
    print('Interpolación espacial exitosa')
    second_interpolator(sequence_of_interpolants)
        
"""    elif (kind_of_measurement == 2):
        flatten_wind_speed = wind_speed[selected_time, height_above_ground, ...].ravel()
        wind_speed_interpolants = griddata(coords_full_set, flatten_wind_speed, coords_to_interp, method='cubic')
        sequence_of_interpolants.append(wind_speed_interpolants)
        
    elif(kind_of_measurement == 3):
        flatten_wind_direction = wind_direction[selected_time, height_above_ground, ...].ravel()
        wind_direction_interpolants = griddata(coords_full_set, flatten_wind_direction, coords_to_interp, method='cubic')
        sequence_of_interpolants.append(wind_direction_interpolants) """
        
    
sequence_of_interpolants = []

kind_of_measurement = int(input('1. Temperatura\n2. Velocidad del viento\n3. Dirección del viento\nIntroduce el número de la medida a interpolar: '))
while (kind_of_measurement in range(1, 4)):
    print('\nInterpolación en proceso...\n')
    first_interpolator(kind_of_measurement, cleaned_dates)
    kind_of_measurement = False