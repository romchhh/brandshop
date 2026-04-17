import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface CatalogState {
    catalogs: any[];
    catalog: any;
    loading: boolean;
    error: string | null;
}

const initialState: CatalogState = {
    catalogs: [],
    catalog: null,
    loading: false,
    error: null,
};

const catalogSlice = createSlice({
    name: 'catalog',
    initialState,
    reducers: {
        fetchCatalogsRequest: (state) => {
            state.loading = true;
            state.error = null;
        },
        fetchCatalogsSuccess: (state, action: PayloadAction<any[]>) => {
            state.loading = false;
            state.catalogs = action.payload;
        },
        fetchCatalogsFailure: (state, action: PayloadAction<string>) => {
            state.loading = false;
            state.error = action.payload;
        },
        fetchCatalogRequest: (state) => {
            state.loading = true;
            state.error = null;
        },
        fetchCatalogSuccess: (state, action: PayloadAction<any[]>) => {
            state.loading = false;
            state.catalog = action.payload;
        },
        fetchCatalogFailure: (state, action: PayloadAction<string>) => {
            state.loading = false;
            state.error = action.payload;
        },
        resetCatalog: (state) => {
            return {
                ...state,
                catalog: null,
            }
        },
    },
});

export const {
    fetchCatalogsRequest,
    fetchCatalogsSuccess,
    fetchCatalogsFailure,
    fetchCatalogRequest,
    fetchCatalogSuccess,
    fetchCatalogFailure,
    resetCatalog
} = catalogSlice.actions;

export default catalogSlice.reducer;
