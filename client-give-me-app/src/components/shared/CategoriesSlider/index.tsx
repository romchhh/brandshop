"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "antd";
import Link from "next/link";
import './styles.css';

interface CategoriesSliderProps {
  catalogs: Array<{
    id: number;
    title: string;
  }>;
}

export const CategoriesSlider = ({ catalogs }: CategoriesSliderProps) => {
  const [showAllCategories, setShowAllCategories] = useState(false);
  const [activeSlide, setActiveSlide] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const scrollContainerRef = useRef(null);

  const handleScroll = (e) => {
    if (scrollContainerRef.current) {
      const scrollPosition = scrollContainerRef.current.scrollLeft;
      const itemWidth = scrollContainerRef.current.offsetWidth;
      const newActiveSlide = Math.round(scrollPosition / itemWidth);
      setActiveSlide(newActiveSlide);
    }
  };

  const handleDotClick = (index) => {
    if (scrollContainerRef.current) {
      const itemWidth = scrollContainerRef.current.offsetWidth;
      scrollContainerRef.current.scrollTo({
        left: itemWidth * index,
        behavior: 'smooth'
      });
    }
  };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setStartX(e.pageX - scrollContainerRef.current.offsetLeft);
    setScrollLeft(scrollContainerRef.current.scrollLeft);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    e.preventDefault();
    const x = e.pageX - scrollContainerRef.current.offsetLeft;
    const walk = (x - startX) * 2;
    scrollContainerRef.current.scrollLeft = scrollLeft - walk;
  };

  const handleTouchStart = (e) => {
    setIsDragging(true);
    setStartX(e.touches[0].pageX - scrollContainerRef.current.offsetLeft);
    setScrollLeft(scrollContainerRef.current.scrollLeft);
  };

  const handleTouchMove = (e) => {
    if (!isDragging) return;
    const x = e.touches[0].pageX - scrollContainerRef.current.offsetLeft;
    const walk = (x - startX) * 2;
    scrollContainerRef.current.scrollLeft = scrollLeft - walk;
  };

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener('mouseup', handleMouseUp);
      container.addEventListener('mouseleave', handleMouseUp);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      if (container) {
        container.removeEventListener('mouseup', handleMouseUp);
        container.removeEventListener('mouseleave', handleMouseUp);
        document.removeEventListener('mouseup', handleMouseUp);
      }
    };
  }, []);

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ 
        padding: '0 16px', 
        marginBottom: 16,
        display: 'flex',
        justifyContent: 'flex-end'
      }}>
        <Button 
          type="text" 
          onClick={() => setShowAllCategories(!showAllCategories)}
          style={{
            height: '32px',
            padding: '0',
            border: 'none',
            color: '#000',
            backgroundColor: 'transparent',
            fontSize: '14px',
            fontWeight: 'bold',
            textDecoration: 'underline',
            boxShadow: 'none'
          }}
        >
          {showAllCategories ? 'Приховати' : 'Показати всі'}
        </Button>
      </div>

      <div style={{ 
        position: 'relative',
        width: '100vw',
        left: '50%',
        right: '50%',
        marginLeft: '-50vw',
        marginRight: '-50vw',
        paddingLeft: '16px',
        paddingRight: '16px',
      }}>
        <div 
          ref={scrollContainerRef}
          className="scroll-container"
          style={{ 
            display: 'flex',
            flexWrap: showAllCategories ? 'wrap' : 'nowrap',
            overflowX: showAllCategories ? 'hidden' : 'auto',
            width: '100%',
            WebkitOverflowScrolling: 'touch',
            gap: '8px',
            paddingBottom: '4px',
            cursor: isDragging ? 'grabbing' : 'grab',
          }}
          onScroll={handleScroll}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleMouseUp}
        >
          {catalogs.map((catalog) => (
            <div 
              key={catalog.id} 
              style={{
                flex: showAllCategories ? '0 0 auto' : '0 0 auto',
                marginBottom: showAllCategories ? '8px' : '0',
              }}
            >
              <Link href={`/catalog/${catalog.id}`}>
                <Button
                  type="text"
                  style={{
                    height: '32px',
                    border: '1px solid #bea35e',
                    borderRadius: '16px',
                    color: '#000',
                    whiteSpace: 'nowrap',
                    padding: '0 12px',
                    fontSize: '14px',
                    minWidth: 'fit-content',
                    userSelect: 'none',
                    WebkitTapHighlightColor: 'transparent',
                    textTransform: 'uppercase'
                  }}
                >
                  {catalog.title}
                </Button>
              </Link>
            </div>
          ))}
        </div>

        {!showAllCategories && (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '6px',
            marginTop: '8px'
          }}>
            {[...Array(Math.ceil(catalogs.length / 3))].map((_, index) => (
              <div
                key={index}
                onClick={() => handleDotClick(index)}
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: index === activeSlide ? '#bea35e' : '#D9D9D9',
                  transition: 'background-color 0.3s',
                  cursor: 'pointer'
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}; 