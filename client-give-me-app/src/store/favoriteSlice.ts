import { createSlice } from '@reduxjs/toolkit';

// Отримуємо збережені обрані товари при ініціалізації
const getInitialState = () => {
    if (typeof window !== 'undefined') {
        const savedFavorites = localStorage.getItem('favorites');
        return {
            items: savedFavorites ? JSON.parse(savedFavorites) : [],
        };
    }
    return { items: [] };
};

const favoriteSlice = createSlice({
    name: 'favorite',
    initialState: getInitialState(),
    reducers: {
        setFavorites: (state, action) => {
            state.items = action.payload;
            // Зберігаємо в localStorage
            localStorage.setItem('favorites', JSON.stringify(action.payload));
        },
        toggleFavorite: (state, action) => {
            const id = action.payload;
            const index = state.items.indexOf(id);
            if (index === -1) {
                state.items.push(id);
            } else {
                state.items.splice(index, 1);
            }
            // Зберігаємо оновлений список в localStorage
            localStorage.setItem('favorites', JSON.stringify(state.items));
        },
    },
});

export const { setFavorites, toggleFavorite } = favoriteSlice.actions;
export default favoriteSlice.reducer;
