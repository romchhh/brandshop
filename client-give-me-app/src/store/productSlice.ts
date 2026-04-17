import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ProductState {
    viewProducts: any[];
    promotionalProducts: any[];
    product: any;
    loading: boolean;
    error: string | null;
}

const initialState: ProductState = {
    viewProducts: [],
    promotionalProducts: [],
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
        fetchPromotionalProductsRequest: (state) => {
            state.loading = true;
            state.error = null;
        },
        fetchPromotionalProductsSuccess: (state, action: PayloadAction<any[]>) => {
            state.loading = false;
            state.promotionalProducts = action.payload;
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
    resetProduct
} = productSlice.actions;

export default productSlice.reducer;
