import {FC, useEffect, useRef} from "react";
import {Input} from "antd";
import {SearchOutlined} from "@ant-design/icons";

import './index.css'

export interface SearchProps {
    placeholder: string,
    handler: () => {},
    onClearSearch?: () => void,
    value?: string,
}

export const Search: FC<SearchProps> = ({placeholder, handler, onClearSearch, value}) => {
    const inputRef = useRef<any>(null);

    useEffect(() => {
        const handleScroll = () => {
            if (inputRef.current) {
                inputRef.current.blur();
            }
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return <div className="search">
        <Input
            ref={inputRef}
            value={value}
            onClear={onClearSearch}
            allowClear
            onChange={handler}
            placeholder={placeholder}
            prefix={<SearchOutlined style={{color: 'rgba(0,0,0,.25)'}}/>}
        /></div>;
};
