import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ProductState {
    viewProducts: any[];
    promotionalProducts: any[];
    promotionalProductsHasNext: boolean;
    promotionalLoadingMore: boolean;
    product: any;
    loading: boolean;
    error: string | null;
}

const initialState: ProductState = {
    viewProducts: [],
    promotionalProducts: [],
    promotionalProductsHasNext: false,
    promotionalLoadingMore: false,
    product: null,
    loading: false,
    error: null,
};

const productSlice = createSlice({
    name: 'product',
    initialState,
    reducers: {
        fetchProductRequest: (state) => {
            state.loading = true;
            state.error = null;
        },
        fetchProductSuccess: (state, action: PayloadAction<any[]>) => {
            state.loading = false;
            state.product = action.payload;
        },
        fetchViewProductsRequest: (state) => {
            state.loading = true;
            state.error = null;
        },
        fetchViewProductsSuccess: (state, action: PayloadAction<any[]>) => {
            state.loading = false;
            state.viewProducts = action.payload;
        },
        fetchPromotionalProductsRequest: (state, action: PayloadAction<{ page?: number; append?: boolean } | void>) => {
            const append = action.payload && typeof action.payload === 'object' && action.payload.append;
            if (append) {
                state.promotionalLoadingMore = true;
            } else {
                state.loading = true;
            }
            state.error = null;
        },
        fetchPromotionalProductsSuccess: (state, action: PayloadAction<any>) => {
            state.loading = false;
            state.promotionalLoadingMore = false;
            const d = action.payload;
            if (Array.isArray(d)) {
                state.promotionalProducts = d;
                state.promotionalProductsHasNext = false;
                return;
            }
            const list = d.results ?? [];
            const append = !!d.append;
            if (append) {
                state.promotionalProducts = [...state.promotionalProducts, ...list];
            } else {
                state.promotionalProducts = list;
            }
            state.promotionalProductsHasNext = !!d.next;
        },
        fetchPromotionalProductsFailure: (state) => {
            state.loading = false;
            state.promotionalLoadingMore = false;
        },
        resetProduct: (state) => ({...state, product: null})
    },
});

export const {
    fetchProductRequest,
    fetchProductSuccess,
    fetchViewProductsSuccess,
    fetchViewProductsRequest,
    fetchPromotionalProductsSuccess,
    fetchPromotionalProductsRequest,
    fetchPromotionalProductsFailure,
    resetProduct
} = productSlice.actions;

export default productSlice.reducer;
