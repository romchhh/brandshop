import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface CatalogState {
    catalogs: any[];
    catalog: any;
    loading: boolean;
    catalogLoadingMore: boolean;
    catalogProductsHasNext: boolean;
    catalogsLoadingMore: boolean;
    catalogsHasNext: boolean;
    error: string | null;
}

const initialState: CatalogState = {
    catalogs: [],
    catalog: null,
    loading: false,
    catalogLoadingMore: false,
    catalogProductsHasNext: false,
    catalogsLoadingMore: false,
    catalogsHasNext: false,
    error: null,
};

const catalogSlice = createSlice({
    name: 'catalog',
    initialState,
    reducers: {
        fetchCatalogsRequest: (
            state,
            action: PayloadAction<{ silent?: boolean; page?: number; append?: boolean } | undefined>,
        ) => {
            const append = !!action.payload?.append;
            const silent = action.payload?.silent;
            if (append) {
                state.catalogsLoadingMore = true;
            } else if (!silent || state.catalogs.length === 0) {
                state.loading = true;
            }
            state.error = null;
        },
        fetchCatalogsSuccess: (state, action: PayloadAction<any[] | { results: any[]; append?: boolean; next?: boolean }>) => {
            state.loading = false;
            state.catalogsLoadingMore = false;
            const pl = action.payload;
            if (Array.isArray(pl)) {
                state.catalogs = pl;
                state.catalogsHasNext = false;
                return;
            }
            const list = pl.results ?? [];
            if (pl.append) {
                const seen = new Set(state.catalogs.map((c) => c.id));
                state.catalogs = [...state.catalogs, ...list.filter((c) => !seen.has(c.id))];
            } else {
                state.catalogs = list;
            }
            state.catalogsHasNext = !!pl.next;
        },
        fetchCatalogsFailure: (state, action: PayloadAction<string>) => {
            state.loading = false;
            state.catalogsLoadingMore = false;
            state.error = action.payload;
        },
        fetchCatalogRequest: (state, action: PayloadAction<
            string | number | { id: string | number; page?: number; append?: boolean }
        >) => {
            const append =
                typeof action.payload === 'object' &&
                action.payload !== null &&
                !!(action.payload as { append?: boolean }).append;
            if (append) {
                state.catalogLoadingMore = true;
            } else {
                state.loading = true;
            }
            state.error = null;
        },
        fetchCatalogSuccess: (state, action: PayloadAction<{ catalog: any; append?: boolean; id?: number } | any>) => {
            state.loading = false;
            state.catalogLoadingMore = false;
            const pl = action.payload;
            const append = pl?.append;
            const data = pl?.catalog ?? pl;
            const prevId = state.catalog?.id;
            if (
                append &&
                String(prevId) === String(data?.id) &&
                Array.isArray(state.catalog?.products) &&
                Array.isArray(data?.products)
            ) {
                state.catalog = {
                    ...data,
                    products: [...state.catalog.products, ...data.products],
                };
            } else {
                state.catalog = data;
            }
            state.catalogProductsHasNext = !!data?.products_has_next;
        },
        fetchCatalogFailure: (state, action: PayloadAction<string>) => {
            state.loading = false;
            state.catalogLoadingMore = false;
            state.error = action.payload;
        },
        resetCatalog: (state) => {
            return {
                ...state,
                catalog: null,
                catalogProductsHasNext: false,
                catalogLoadingMore: false,
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
