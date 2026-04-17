import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UserState {
    user: any;
    loading: boolean;
}

const initialState: UserState = {
    user: null,
    loading: false,
};

const userSlice = createSlice({
    name: 'user',
    initialState,
    reducers: {
        fetchUserRequest: (state) => {
            return {
                ...state,
                loading: true,
            }
        },
        fetchUserSuccess: (state, action: PayloadAction<any[]>) => {
            return {
                ...state,
                loading: false,
                user: action.payload,
            }
        },
    },
});

export const {
    fetchUserRequest,
    fetchUserSuccess
} = userSlice.actions;

export default userSlice.reducer;
