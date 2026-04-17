"use client";

import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Button, List } from "antd";
import { useInitData } from '@telegram-apps/sdk-react';
import Link from "next/link";
import _ from 'lodash';
import { Search } from "@/components/shared/Search";
import './styles.css';
import classNames from "classnames";

import { RootState } from "@/store/store";
import { fetchViewProductsRequest, fetchPromotionalProductsRequest, fetchNewProductsRequest } from "@/store/productSlice";
import { ProductPreview } from "@/components/shared/ProductPreview";
import { getUserId } from "@/lib/helpers";
import { emptyText } from "@/components/shared/EmptyText";
import { fetchCatalogsRequest } from "@/store/catalogSlice";
import { CategoriesSlider } from "@/components/shared/CategoriesSlider";

const groupProduct = (products) => _.groupBy(products, 'catalog_title');

const ITEMS_PER_PAGE = 10;

const getNewProducts = (catalogs) => {
    const newProducts = [];
    catalogs?.forEach(catalog => {
        const topProducts = catalog.products.slice(0, 4).map(product => ({
            ...product,
            catalog_title: catalog.title
        }));
        newProducts.push(...topProducts);
    });
    return newProducts;
}

const Home = () => {
  const dispatch = useDispatch();
  const viewProducts = useSelector((state: RootState) => state.product.viewProducts);
  const promotionalProducts = useSelector((state: RootState) => state.product.promotionalProducts);
  const catalogs = useSelector((state: RootState) => state.catalog.catalogs);
  const [products, setProducts] = useState(null);
  const [promoProducts, setPromoProducts] = useState(null);
  const [newProductsList, setNewProductsList] = useState(null);
  const initData = useInitData(true);
  const [filteredProducts, setFilteredProducts] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [visibleItems, setVisibleItems] = useState(ITEMS_PER_PAGE);
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    if (initData) {
      dispatch(fetchViewProductsRequest(getUserId(initData)));
      dispatch(fetchPromotionalProductsRequest());
      dispatch(fetchCatalogsRequest());
    }
  }, [initData]);

  useEffect(() => {
    if (viewProducts) {
      setProducts(viewProducts.slice(0, 4));
    }
  }, [viewProducts]);

  useEffect(() => {
    if (promotionalProducts) {
      setPromoProducts(promotionalProducts.slice(0, 4));
    }
  }, [promotionalProducts]);

  useEffect(() => {
    if (catalogs) {
      const newProducts = getNewProducts(catalogs);
      setNewProductsList(newProducts.slice(0, 4));
    }
  }, [catalogs]);

  useEffect(() => {
    if (catalogs) {
      const allProducts = catalogs.flatMap(catalog => 
        catalog.products.map(product => ({
          ...product,
          catalog_title: catalog.title
        }))
      );
    }
  }, [catalogs]);

  useEffect(() => {
    if (typeof window !== "undefined") {
        const savedSearch = localStorage.getItem('searchValue');
        if (savedSearch) {
            setSearchValue(savedSearch);
            setIsSearching(true);
            const allProducts = catalogs?.flatMap(catalog => 
                catalog.products.map(product => ({
                    ...product,
                    catalog_title: catalog.title
                }))
            ) || [];
            setFilteredProducts(allProducts.filter((product) =>
                product.title.toLowerCase().includes(savedSearch.toLowerCase())
            ));
        }
    }
    }, [catalogs]);

    const onSearch = (event) => {
        const value = event.target.value;
        setSearchValue(value);
        if (value) {
            setIsSearching(true);
            if (typeof window !== "undefined") {
                localStorage.setItem('searchValue', value);
            }
            const allProducts = catalogs.flatMap(catalog => 
                catalog.products.map(product => ({
                    ...product,
                    catalog_title: catalog.title
                }))
            );
            setFilteredProducts(allProducts.filter((product) =>
                product.title.toLowerCase().includes(value.toLowerCase())
            ));
        } else {
            setIsSearching(false);
            setFilteredProducts(null);
            setSearchValue('');
            if (typeof window !== "undefined") {
                localStorage.removeItem('searchValue');
            }
        }
    };

  const onClearSearch = () => {
    setIsSearching(false);
    setFilteredProducts(null);
    setSearchValue('');
    localStorage.removeItem('searchValue');
  };

  useEffect(() => {
    setVisibleItems(ITEMS_PER_PAGE);
  }, [filteredProducts]);

  const getDisplayedProducts = () => {
    const allProducts = filteredProducts || catalogs?.flatMap(catalog => 
      catalog.products.map(product => ({
        ...product,
        catalog_title: catalog.title
      }))
    ) || [];
    
    return allProducts.slice(0, visibleItems);
  };

  const loadMore = () => {
    setVisibleItems(prev => prev + ITEMS_PER_PAGE);
  };

  const handleScroll = () => {
    if (
      window.innerHeight + document.documentElement.scrollTop
      === document.documentElement.offsetHeight
    ) {
      loadMore();
    }
  };

  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    return () => {
        if (typeof window !== "undefined") {
            if (!window.location.pathname.includes('/products/')) {
                localStorage.removeItem('searchValue');
            }
        }
    };
}, []);

  return (
    <div>
      <Search 
        placeholder="Пошук товару" 
        handler={onSearch} 
        onClear={onClearSearch}
        value={searchValue}
      />
      
      {catalogs && <CategoriesSlider catalogs={catalogs} />}

      {!isSearching && products && products.length > 0 && (
        <>
          <h2 style={{ marginTop: 40, marginBottom: 20, fontSize: 24 }}>Переглянуті товари</h2>
          
          <List
            locale={{ emptyText }}
            grid={{ gutter: 16, column: 2 }}
            dataSource={products}
            className={classNames("list-product-item")}
            style={{ marginTop: 20 }}
            renderItem={(item) => (
              <ProductPreview {...item} />
            )}
          />

          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center',
            marginTop: 20,
            marginBottom: 20
          }}>
            <Link href="/views" style={{ width: '100%' }}>
              <Button 
                type="text" 
                style={{
                  width: '100%',
                  height: '48px',
                  border: '1px solid #bea35e',
                  borderRadius: '24px',
                  color: '#bea35e',
                  backgroundColor: '#fff'
                }}
              >
                ПОКАЗАТИ ЩЕ
              </Button>
            </Link>
            <div style={{
              width: '100%',
              height: '1px',
              backgroundColor: '#E8E8E8',
              marginTop: 20
            }} />
          </div>
        </>
      )}

      {!isSearching && newProductsList && newProductsList.length > 0 && (
        <>
          <h2 style={{ marginTop: 40, marginBottom: 20, fontSize: 24 }}>Новинки</h2>
          
          <List
            locale={{ emptyText }}
            grid={{ gutter: 16, column: 2 }}
            dataSource={newProductsList}
            className={classNames("list-product-item")}
            style={{ marginTop: 20 }}
            renderItem={(item) => (
              <ProductPreview {...item} />
            )}
          />

          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center',
            marginTop: 20,
            marginBottom: 20
          }}>
            <Link href="/new_products" style={{ width: '100%' }}>
              <Button 
                type="text" 
                style={{
                  width: '100%',
                  height: '48px',
                  border: '1px solid #bea35e',
                  borderRadius: '24px',
                  color: '#bea35e',
                  backgroundColor: '#fff'
                }}
              >
                ПОКАЗАТИ ЩЕ
              </Button>
            </Link>
            <div style={{
              width: '100%',
              height: '1px',
              backgroundColor: '#E8E8E8',
              marginTop: 20
            }} />
          </div>
        </>
      )}

      {!isSearching && promoProducts && promoProducts.length > 0 && (
        <>
          <h2 style={{ marginTop: 40, marginBottom: 20, fontSize: 24 }}>Акційні пропозиції</h2>
          
          <List
            locale={{ emptyText }}
            grid={{ gutter: 16, column: 2 }}
            dataSource={promoProducts}
            style={{ marginTop: 20 }}
            className={classNames("list-product-item")}
            renderItem={(item) => (
              <ProductPreview {...item} />
            )}
          />

          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center',
            marginTop: 20,
            marginBottom: 20
          }}>
            <Link href="/promotional-offers" style={{ width: '100%' }}>
              <Button 
                type="text" 
                style={{
                  width: '100%',
                  height: '48px',
                  border: '1px solid #bea35e',
                  borderRadius: '24px',
                  color: '#bea35e',
                  backgroundColor: '#fff'
                }}
              >
                ПОКАЗАТИ ЩЕ
              </Button>
            </Link>
            <div style={{
              width: '100%',
              height: '1px',
              backgroundColor: '#E8E8E8',
              marginTop: 20
            }} />
          </div>
        </>
      )}

      {catalogs && (
        <>
          <h2 style={{ marginTop: 40, marginBottom: 20, fontSize: 24 }}>Всі товари</h2>
          
          <List
            locale={{ emptyText }}
            grid={{ gutter: 16, column: 2 }}
            dataSource={getDisplayedProducts()}
            style={{ marginTop: 20 }}
            className={classNames("list-product-item")}
            renderItem={(item) => (
              <ProductPreview {...item} />
            )}
          />
        </>
      )}
    </div>
  );
};

export default Home;