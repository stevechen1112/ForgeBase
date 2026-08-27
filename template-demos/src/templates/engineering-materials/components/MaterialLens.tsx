"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, RotateCcw } from "lucide-react";
import type { TemplateProduct } from "@/contracts/forgebase";
import { materialsBase } from "../data";
import styles from "./Materials.module.css";

const axes = [
  {key:"thermal",label:"Heat",options:["Moderate","Elevated","Cyclic"]},
  {key:"load",label:"Load",options:["Light","Structural","Wear contact"]},
  {key:"priority",label:"Priority",options:["Low mass","Insulation","Machinability"]},
] as const;

const scores: Record<string, number[]> = {
  "therma-px-620":[88,61,92],
  "aerion-a7-58":[68,91,73],
  "cerava-c9-94":[96,78,84],
};

export function MaterialLens({ products, embedded=false }: { products: TemplateProduct[]; embedded?: boolean }) {
  const [selected,setSelected]=useState([1,1,1]);
  const ranking=useMemo(()=>products.map((product,index)=>({product,score:scores[product.slug][0]-Math.abs(selected[0]-index)*7+scores[product.slug][1]-Math.abs(selected[1]-index)*5+scores[product.slug][2]-Math.abs(selected[2]-index)*4})).sort((a,b)=>b.score-a.score),[products,selected]);
  return <section className={embedded?styles.lensEmbedded:styles.lens}>
    <header><div><span>MATERIAL LENS / DEMO</span><h2>Turn conditions into a shortlist.</h2></div><button type="button" onClick={()=>setSelected([1,1,1])}><RotateCcw/>Reset</button></header>
    <div className={styles.lensBody}><div className={styles.lensAxes}>{axes.map((axis,axisIndex)=><section key={axis.key}><span>0{axisIndex+1} / {axis.label}</span><div>{axis.options.map((option,optionIndex)=><button type="button" key={option} aria-pressed={selected[axisIndex]===optionIndex} onClick={()=>setSelected(selected.map((value,index)=>index===axisIndex?optionIndex:value))}>{option}</button>)}</div></section>)}</div><div className={styles.lensResults}><span>ILLUSTRATIVE RANKING</span>{ranking.map((item,index)=><article key={item.product.id}><b>0{index+1}</b><div><h3>{item.product.name}</h3><p>{item.product.shortDescription}</p></div><strong>{Math.min(96,Math.round(item.score/3))}<small>/100</small></strong><Link href={`${materialsBase}/products/${item.product.slug}/`}>Evidence <ArrowRight/></Link></article>)}<small>Scores are fictional UI behavior, not engineering recommendations.</small></div></div>
  </section>;
}
