"use client";

import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Button, List } from "antd";
import { useInitData } from '@telegram-apps/sdk-react';
import Link from "next/link";
import axios from "axios";
import { Search } from "@/components/shared/Search";
import './styles.css';
import classNames from "classnames";

import { RootState } from "@/store/store";
import { fetchViewProductsRequest } from "@/store/productSlice";
import { ProductPreview } from "@/components/shared/ProductPreview";
import { getUserId } from "@/lib/helpers";
import { emptyText } from "@/components/shared/EmptyText";
import { CategoriesSlider } from "@/components/shared/CategoriesSlider";
import { API_HOST } from "@/lib/constants";
import { beginPageWork } from "@/lib/pageWork";

const Home = () => {
  const dispatch = useDispatch();
  const viewProducts = useSelector((state: RootState) => state.product.viewProducts);
  const [catalogs, setCatalogs] = useState<any[] | null>(null);
  const [products, setProducts] = useState<any[] | null>(null);
  const [promoProducts, setPromoProducts] = useState<any[] | null>(null);
  const [newProductsList, setNewProductsList] = useState<any[] | null>(null);
  const [feedProducts, setFeedProducts] = useState<any[]>([]);
  const initData = useInitData(true);
  const [searchHits, setSearchHits] = useState<any[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    let cancelled = false;
    const finish = beginPageWork();
    axios
      .get(`${API_HOST}/api/home/`)
      .then((res) => {
        if (cancelled) return;
        setCatalogs(res.data.catalogs || []);
        setNewProductsList(res.data.new_products || []);
        setPromoProducts(res.data.promotional_products || []);
        setFeedProducts(res.data.products || []);
      })
      .catch(() => {
        if (!cancelled) {
          setCatalogs([]);
          setNewProductsList([]);
          setPromoProducts([]);
          setFeedProducts([]);
        }
      })
      .finally(finish);
    return () => {
      cancelled = true;
      finish();
    };
  }, []);

  useEffect(() => {
    if (!initData) return;
    dispatch(fetchViewProductsRequest(getUserId(initData)));
  }, [initData, dispatch]);

  useEffect(() => {
    if (viewProducts) setProducts(viewProducts.slice(0, 4));
  }, [viewProducts]);

  useEffect(() => {
    const q = searchValue.trim();
    if (q.length < 2) {
      setIsSearching(false);
      setSearchHits(null);
      return;
    }
    setIsSearching(true);
    const timer = window.setTimeout(() => {
      axios
        .get(`${API_HOST}/api/products/search/`, { params: { q } })
        .then((res) => setSearchHits(res.data || []))
        .catch(() => setSearchHits([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchValue]);

  const onSearch = (event) => {
    setSearchValue(event.target.value);
  };

  const onClearSearch = () => {
    setIsSearching(false);
    setSearchHits(null);
    setSearchValue('');
  };

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
            renderItem={(item, index) => (
              <ProductPreview {...item} imagePriority={index < 2} />
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

      {(isSearching || feedProducts.length > 0) && (
        <>
          <h2 style={{ marginTop: 40, marginBottom: 20, fontSize: 24 }}>
            {isSearching ? "Пошук" : "Всі товари"}
          </h2>
          
          <List
            locale={{ emptyText }}
            grid={{ gutter: 16, column: 2 }}
            dataSource={isSearching ? (searchHits || []) : feedProducts}
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