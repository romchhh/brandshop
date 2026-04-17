import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { map, when, propEq, assoc } from 'ramda'

interface BasketItemState {
    basketItems: any[];
    basketItem: any;
    loading: boolean;
    error: string | null;
}

const initialState: BasketItemState = {
    basketItems: [],
    basketItem: null,
    loading: false,
    error: null,
};

const basketItemSlice = createSlice({
    name: 'basketItem',
    initialState,
    reducers: {
        fetchBasketItemsRequest: (state) => {
            return {
                ...state,
                loading: true,
                error: null,
            }
        },
        fetchBasketItemsSuccess: (state, action: PayloadAction<any[]>) => {
            return {
                ...state,
                loading: false,
                basketItems: action.payload,
            }
        },
        updateBasketItemRequest: (state) => state,
        updateBasketItemSuccess: (state, action: PayloadAction<any[]>) => {
            const { id, quantity } = action.payload
            return {
                ...state,
                basketItem: state.basketItem?.id === id ? { ...state.basketItem, quantity } : state.basketItem,
                basketItems: state.basketItems.map(el => el.id == id ? {...el, quantity} : el)
            }
        },
        setBasketItemSuccess: (state, action: PayloadAction<any[]>) => {
            return {
                ...state,
                basketItem: action.payload
            }
        },
        deleteBasketItemRequest: (state) => state,
        deleteBasketItemSuccess: (state, action: PayloadAction<any[]>) => {
            const { id } = action.payload
            return {
                ...state,
                basketItems: state.basketItems.filter((el) => el.id !== id)
            }
        },
        createBasketItemRequest: (state) => state,
        resetBasketItems: (state) => {
            return {
                ...state,
                basketItems: []
            }
        },
    },
});

export const {
    fetchBasketItemsRequest,
    fetchBasketItemsSuccess,
    updateBasketItemRequest,
    updateBasketItemSuccess,
    deleteBasketItemRequest,
    deleteBasketItemSuccess,
    createBasketItemRequest,
    resetBasketItems,
    setBasketItemSuccess,
} = basketItemSlice.actions;

export default basketItemSlice.reducer;
