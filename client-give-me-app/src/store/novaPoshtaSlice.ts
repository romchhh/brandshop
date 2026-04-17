import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface NovePoshtaState {
    cities: any[];
    warehouses: any[];
    citiesLoading: boolean;
    warehousesLoading: boolean;
}

const initialState: NovePoshtaState = {
    cities: [],
    warehouses: [],
    citiesLoading: false,
    warehousesLoading: false,
};

const novaPoshtaSlice = createSlice({
    name: 'novaPoshta',
    initialState,
    reducers: {
        fetchCitiesRequest: (state) => {
            return {
                ...state,
                citiesLoading: true,
            }
        },
        fetchCitiesSuccess: (state, action: PayloadAction<any[]>) => {
            return {
                ...state,
                citiesLoading: false,
                cities: action.payload,
            }
        },
        fetchWarehousesRequest: (state) => {
            return {
                ...state,
                warehousesLoading: true,
            }
        },
        fetchWarehousesSuccess: (state, action: PayloadAction<any[]>) => {
            return {
                ...state,
                warehousesLoading: false,
                warehouses: action.payload,
            }
        },
        resetCities: (state) => {
            return {
                ...state,
                cities: [],
            }
        },
        resetWarehouses: (state) => {
            return {
                ...state,
                warehouses: [],
            }
        },
    },
});

export const {
    fetchCitiesSuccess,
    fetchWarehousesSuccess,
    fetchWarehousesRequest,
    fetchCitiesRequest,
    resetWarehouses,
    resetCities
} = novaPoshtaSlice.actions;

export default novaPoshtaSlice.reducer;
