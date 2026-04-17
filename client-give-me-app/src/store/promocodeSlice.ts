import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { map, when, propEq, assoc } from 'ramda'

interface PromocodeState {
    promocode: any;
    loading: boolean;
}

const initialState: PromocodeState = {
    promocode: null,
    loading: false,
};

const promocodeSlice = createSlice({
    name: 'promocode',
    initialState,
    reducers: {
        fetchPromocodeRequest: (state) => {
            return {
                ...state,
                loading: true,
            }
        },
        fetchPromocodeSuccess: (state, action: PayloadAction<any[]>) => {
            return {
                ...state,
                loading: false,
                promocode: action.payload,
            }
        },
        resetPromocode: (state) => {
            return {
                ...state,
                promocode: null,
            }
        },
    },
});

export const {
    fetchPromocodeRequest,
    fetchPromocodeSuccess,
    resetPromocode
} = promocodeSlice.actions;

export default promocodeSlice.reducer;
