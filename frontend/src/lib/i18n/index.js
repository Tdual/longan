import { ja } from './ja.js';

// 現在の言語（デフォルトは日本語）
let currentLang = 'ja';

// 翻訳データ
const translations = {
  ja
};

/**
 * 翻訳関数
 * @param {string} key - 翻訳キー（ドット区切り）
 * @param {object} params - 置換パラメータ
 * @returns {string} 翻訳されたテキスト
 */
export function t(key, params = {}) {
  const keys = key.split('.');
  let value = translations[currentLang];
  
  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = value[k];
    } else {
      // キーが見つからない場合はキー自体を返す
      console.warn(`Translation key not found: ${key}`);
      return key;
    }
  }
  
  // パラメータ置換
  if (typeof value === 'string' && Object.keys(params).length > 0) {
    return value.replace(/\{(\w+)\}/g, (match, param) => {
      return params[param] !== undefined ? params[param] : match;
    });
  }
  
  return value;
}

/**
 * 現在の言語を取得
 */
export function getCurrentLang() {
  return currentLang;
}

/**
 * 言語を設定
 */
export function setLang(lang) {
  if (translations[lang]) {
    currentLang = lang;
  } else {
    console.warn(`Language not supported: ${lang}`);
  }
}