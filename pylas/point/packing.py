""" This module contains functions to pack and unpack point dimensions
"""
import numpy as np


def least_significant_bit(val):
    """ Return the least significant bit
    """
    return (val & -val).bit_length() - 1


def unpack(source_array, mask, dtype=np.uint8):
    """ Unpack sub field using its mask

    Parameters:
    ----------
    source_array : numpy.ndarray
        The source array
    mask : mask (ie: 0b00001111)
        Mask of the sub field to be extracted from the source array
    Returns
    -------
    numpy.ndarray
        The sub field array
    """
    lsb = least_significant_bit(mask)
    return ((source_array & mask) >> lsb).astype(dtype)


def pack(array, sub_field_array, mask, inplace=False):
    """ Packs a sub field's array into another array using a mask

    Parameters:
    ----------
    array : numpy.ndarray
        The array in which the sub field array will be packed into
    array_in : numpy.ndarray
        sub field array to pack
    mask : mask (ie: 0b00001111)
        Mask of the sub field
    inplace : {bool}, optional
        If true a new array is returned. (the default is False, which modifies the array in place)

    Raises
    ------
    OverflowError
        If the values contained in the sub field array are greater than its mask's number of bits
        allows
    """
    lsb = least_significant_bit(mask)
    max_value = int(mask >> lsb)
    if sub_field_array.max() > max_value:
        raise OverflowError(
            "value ({}) is greater than allowed (max: {})".format(
                sub_field_array.max(), max_value
            )
        )
    if inplace:
        array[:] = array & ~mask
        array[:] = array | ((sub_field_array << lsb) & mask).astype(array.dtype)
    else:
        array = array & ~mask
        return array | ((sub_field_array << lsb) & mask).astype(array.dtype)


def unpack_sub_fields(data, point_format):
    """ Unpack all the composed fields of the structured_array into their corresponding
    sub-fields

    Returns:
        A new structured array with the sub-fields de-packed
    """
    composed_dims = point_format.composed_fields
    dtype = point_format.dtype
    point_record = np.zeros_like(data, dtype)

    for dim_name in data.dtype.names:
        if dim_name in composed_dims:
            for sub_field in composed_dims[dim_name]:
                point_record[sub_field.name] = unpack(data[dim_name], sub_field.mask)
        else:
            point_record[dim_name] = data[dim_name]
    return point_record


def repack_sub_fields(structured_array, point_format):
    """ Repack all the sub-fields of the structured_array into their corresponding
    composed fields

    Returns:
        A new structured array without the de-packed sub-fields
    """
    dtype = point_format.dtype
    composed_dims = point_format.composed_fields
    repacked_array = np.zeros_like(structured_array, dtype)

    for dim_name in repacked_array.dtype.names:
        if dim_name in composed_dims:
            _repack_composed_dim(dim_name, composed_dims[dim_name], repacked_array, structured_array)
        else:
            repacked_array[dim_name] = structured_array[dim_name]
    return repacked_array


def _repack_composed_dim(dim_name, sub_fields, repacked_array, structured_array):
    """ Repack the fields of a composed dimension together

    Parameters
    ----------
    sub_fields: list of SubField, the sub fields of the dimension
    dim_name: name of the composed dimension
    repacked_array: structured array in which the composed_dim will be repacked
    structured_array: structured array from which sub fields are taken

    Raises
    ------

    OverflowError if the values in any of the sub fields are greater than
    allowed

    """
    for sub_field in sub_fields:
        try:
            pack(
                repacked_array[dim_name],
                structured_array[sub_field.name],
                sub_field.mask,
                inplace=True,
            )
        except OverflowError as e:
            raise OverflowError(
                "Error repacking {} into {}: {}".format(
                    sub_field.name, dim_name, e
                )
            )
