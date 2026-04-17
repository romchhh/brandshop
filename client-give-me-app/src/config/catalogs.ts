// Каталоги з числовими розмірами (одяг)
export const numericSizeCatalogs = [
    '1',  // Джинси
    '11', // Штани
    '17', // Шорти
] as const;

// Каталоги з розмірами взуття
export const shoeSizeCatalogs = [
    '3',  // Взуття весна/осінь
    '4',  // Взуття зима
    '5',  // Взуття літо
] as const;

// Каталоги з буквеними розмірами (одяг)
export const letterSizeCatalogs = [
    '2',   // Светри
    '6',   // Костюми Весна/осінь
    '7',   // Зимові костюми
    '8',   // Костюми літні
    '9',   // Куртки
    '10',  // Жилетки
    '12',  // Спортивні штани
    '13',  // Футболки
    '14',  // Поло
    '15',  // Сорочки
    '16',  // Білизна
    '18',  // Шорти плавальні
] as const;

export const sizesOptions = {
    numeric: [
        { label: "28", value: "28" },
        { label: "29", value: "29" },
        { label: "30", value: "30" },
        { label: "31", value: "31" },
        { label: "32", value: "32" },
        { label: "33", value: "33" },
        { label: "34", value: "34" },
        { label: "35", value: "35" },
        { label: "36", value: "36" },
        { label: "38", value: "38" },
        { label: "39", value: "39" },
        { label: "40", value: "40" },
        { label: "41", value: "41" },
        { label: "42", value: "42" },
        { label: "43", value: "43" },
        { label: "44", value: "44" },
        { label: "45", value: "45" },
        { label: "46", value: "46" },
    ],
    shoe: [
        { label: "38", value: "38" },
        { label: "39", value: "39" },
        { label: "40", value: "40" },
        { label: "41", value: "41" },
        { label: "42", value: "42" },
        { label: "43", value: "43" },
        { label: "44", value: "44" },
        { label: "45", value: "45" },
        { label: "46", value: "46" },
        { label: "47", value: "47" },
    ],
    letter: [
        { label: "S", value: "S" },
        { label: "M", value: "M" },
        { label: "L", value: "L" },
        { label: "XL", value: "XL" },
        { label: "2XL", value: "2XL" },
        { label: "3XL", value: "3XL" },
        { label: "4XL", value: "4XL" },
        { label: "5XL", value: "5XL" },
        { label: "6XL", value: "6XL" },
        { label: "7XL", value: "7XL" },
    ]
} as const; 