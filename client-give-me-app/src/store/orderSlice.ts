import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { map, when, propEq, assoc } from 'ramda'

interface OrderState {
    orders: any[];
    loading: boolean;
    error: string | null;
}

const initialState: OrderState = {
    orders: [],
    loading: false,
    error: null,
};

const orderSlice = createSlice({
    name: 'order',
    initialState,
    reducers: {
        fetchOrdersRequest: (state) => {
            return {
                ...state,
                loading: true,
                error: null,
            }
        },
        fetchOrdersSuccess: (state, action: PayloadAction<any[]>) => {
            return {
                ...state,
                loading: false,
                orders: action.payload,
            }
        },
        createOrderRequest: (state) => state,
        resetOrders: (state) => {
            return {
                ...state,
                orders: [],
            }
        },
    },
});

export const {
    fetchOrdersSuccess,
    fetchOrdersRequest,
    createOrderRequest,
    resetOrders,
} = orderSlice.actions;

export default orderSlice.reducer;
