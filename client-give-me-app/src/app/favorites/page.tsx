"use client";

import {Flex, List} from 'antd';
import {Search} from "@/components/shared/Search";
import {useDispatch, useSelector} from "react-redux";
import {RootState} from "@/store/store";
import {useEffect, useState} from "react";
import {useMount} from "react-use";
import {fetchCatalogsRequest} from "@/store/catalogSlice";
import {ProductPreview} from "@/components/shared/ProductPreview";
import {emptyText} from "@/components/shared/EmptyText";
import classNames from "classnames";

function FavoritesPage() {
    const dispatch = useDispatch();
    const catalogs = useSelector((state: RootState) => state.catalog.catalogs);
    const favoriteIds = useSelector((state: RootState) => state.favorite.items);
    const [favoriteProducts, setFavoriteProducts] = useState([]);

    const onSearch = (event) => {
        const value = event.target.value.toLowerCase();
        const filteredProducts = getAllFavoriteProducts().filter(product => 
            product.title.toLowerCase().includes(value)
        );
        setFavoriteProducts(filteredProducts);
    };

    const onClearSearch = () => {
        setFavoriteProducts(getAllFavoriteProducts());
    };

    const getAllFavoriteProducts = () => {
        const products = [];
        catalogs.forEach(catalog => {
            catalog.products.forEach(product => {
                if (favoriteIds.includes(product.id)) {
                    products.push({
                        ...product,
                        catalog_title: catalog.title
                    });
                }
            });
        });
        return products;
    };

    useMount(() => {
        dispatch(fetchCatalogsRequest());
    });

    useEffect(() => {
        setFavoriteProducts(getAllFavoriteProducts());
    }, [catalogs, favoriteIds]);

    return <>
        <Flex justify="center">
            <h1>Обране</h1>
        </Flex>
        <Search placeholder="Пошук товару" handler={onSearch} onClear={onClearSearch}/>
        <List
            locale={{ emptyText }}
            grid={{gutter: 16, column: 2}}
            dataSource={favoriteProducts}
            className={classNames("list-product-item")}
            style={{marginTop: 20}}
            renderItem={(item) => (
                <ProductPreview {...item}/>
            )}
        />
    </>;
}

export default FavoritesPage; 