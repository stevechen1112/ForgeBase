"use client";

import Image from "next/image";
import { useMemo, useState } from "react";
import { ArrowRight, Check, Search, SlidersHorizontal, X } from "lucide-react";
import { DemoCTA } from "@/components/DemoCTA";
import type { TemplateCategory, TemplateProduct } from "@/contracts/forgebase";
import styles from "./Electronics.module.css";

const electronicsBase = "/templates/electronic-components";
const productImages: Record<string, string> = {
  "cat-connectors": `${electronicsBase}/mezzanine-connector-macro.png`,
  "cat-protection": `${electronicsBase}/protection-device-reel.png`,
  "cat-sensors": `${electronicsBase}/component-family-hero.png`,
};

export function ParametricCatalog({ products, categories, embedded = false }: { products: TemplateProduct[]; categories: TemplateCategory[]; embedded?: boolean }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [compare, setCompare] = useState<string[]>([]);

  const filtered = useMemo(() => products.filter((product) => {
    const haystack = [product.name, product.modelNumber, product.shortDescription, ...product.attributes.flatMap((attribute) => [attribute.label, attribute.value])].join(" ").toLowerCase();
    return (category === "all" || product.categoryId === category) && haystack.includes(query.toLowerCase());
  }), [category, products, query]);

  function toggleCompare(id: string) {
    setCompare((current) => current.includes(id) ? current.filter((item) => item !== id) : current.length < 3 ? [...current, id] : current);
  }

  const comparedProducts = products.filter((product) => compare.includes(product.id));

  return <section className={embedded ? styles.catalogEmbedded : styles.catalogTool}>
    <div className={styles.filterBar}>
      <label className={styles.searchField}><Search size={18} /><span className={styles.srOnly}>Search parts</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search part number, package or parameter" /></label>
      <label className={styles.categoryField}><SlidersHorizontal size={17} /><span className={styles.srOnly}>Filter category</span><select value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All families</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <span className={styles.resultCount}>{filtered.length} / {products.length} PARTS</span>
    </div>

    <div className={styles.partTableWrap}>
      <table className={styles.partTable}>
        <thead><tr><th>Compare</th><th>Part</th><th>Family</th><th>Key parameter</th><th>Package / format</th><th>Demo status</th><th /></tr></thead>
        <tbody>{filtered.map((product) => {
          const selected = compare.includes(product.id);
          return <tr key={product.id}>
            <td><button type="button" className={selected ? styles.compareSelected : styles.compareButton} aria-label={`${selected ? "Remove" : "Add"} ${product.name} ${selected ? "from" : "to"} comparison`} onClick={() => toggleCompare(product.id)}>{selected ? <Check size={15} /> : "+"}</button></td>
            <td><div className={styles.partIdentity}><span className={styles.partThumb}><Image src={productImages[product.categoryId ?? ""]} alt="" fill sizes="52px" /></span><div><b>{product.modelNumber}</b><small>{product.name}</small></div></div></td>
            <td>{categories.find((item) => item.id === product.categoryId)?.name}</td>
            <td><b>{product.attributes[0].value}</b><small>{product.attributes[0].label}</small></td>
            <td><b>{product.attributes[3].value}</b><small>{product.attributes[3].label}</small></td>
            <td><span className={styles.demoStatus}>DEMO DATA</span></td>
            <td><DemoCTA cta={product.cta} className={styles.rowLink}>View <ArrowRight size={15} /></DemoCTA></td>
          </tr>;
        })}</tbody>
      </table>
      {filtered.length === 0 && <div className={styles.emptyState}>No Demo parts match this filter.</div>}
    </div>

    {compare.length > 0 && <div className={styles.compareTray}><span>{compare.length} SELECTED</span><div>{comparedProducts.map((product) => <button type="button" key={product.id} onClick={() => toggleCompare(product.id)}>{product.modelNumber}<X size={13} /></button>)}</div><a href="#comparison">Compare parameters <ArrowRight size={15} /></a></div>}

    <div id="comparison" className={styles.compareMatrix}>
      <div className={styles.matrixTitle}><span>PARAMETRIC COMPARISON</span><p>{comparedProducts.length ? "Showing selected Demo parts." : "Select up to three parts above; the complete Demo set is shown by default."}</p></div>
      <div className={styles.matrixScroll}><table><thead><tr><th>Parameter</th>{(comparedProducts.length ? comparedProducts : products).map((product) => <th key={product.id}>{product.modelNumber}</th>)}</tr></thead><tbody>{[0,1,2,3,4].map((index) => <tr key={index}><th>{products[0].attributes[index].label}</th>{(comparedProducts.length ? comparedProducts : products).map((product) => <td key={product.id}>{product.attributes[index]?.value ?? "—"}</td>)}</tr>)}</tbody></table></div>
    </div>
  </section>;
}
