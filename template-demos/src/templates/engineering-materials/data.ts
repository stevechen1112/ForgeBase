import type { TemplateDemoData } from "@/contracts/forgebase";

export const materialsBase = "/templates/engineering-materials";

export const engineeringMaterialsData: TemplateDemoData = {
  site: {
    companyName: "Matera Materials",
    legalNotice: "Demonstration company — not a registered material producer, distributor or testing laboratory",
    tagline: "Choose by evidence. Not instinct.",
    description: "A ForgeBase website template for engineering-material suppliers and technical selection teams.",
    email: "materials-demo@example.com",
    phone: "+00 000 000 000",
    location: "Demonstration technical region",
    disclosure: { label: "Material Selection Preview", message: "All grades, properties, test records, compliance statements, availability and company details are illustrative." },
  },
  ctas: [
    { id: "materials-nav-sample", label: "Request a sample", href: `${materialsBase}/rfq/`, intent: "request_sample", variant: "primary" },
    { id: "materials-lens", label: "Open Material Lens", href: `${materialsBase}/products/`, intent: "view_product", variant: "primary" },
    { id: "materials-docs", label: "Review Demo documents", href: `${materialsBase}/resources/`, intent: "download_spec", variant: "secondary" },
    { id: "materials-consult", label: "Discuss an application", href: `${materialsBase}/rfq/`, intent: "ask_question", variant: "text" },
    { id: "materials-submit", label: "Prepare sample brief", href: `${materialsBase}/rfq/`, intent: "request_sample", variant: "primary" },
  ],
  categories: [
    { id: "cat-polymers", slug: "performance-polymers", name: "Performance polymers", description: "Thermal, wear and chemical-resistance concepts spanning stock shapes and engineered components." },
    { id: "cat-alloys", slug: "lightweight-alloys", name: "Lightweight alloys", description: "Low-mass metallic concepts organized around strength, process route and environmental exposure." },
    { id: "cat-ceramics", slug: "technical-ceramics", name: "Technical ceramics", description: "Wear, electrical and thermal-management concepts for demanding component environments." },
  ],
  products: [
    { id:"grade-therma-px",slug:"therma-px-620",name:"THERMA / PX-620",modelNumber:"PX-620 DEMO GRADE",shortDescription:"A fictional high-temperature polymer grade for dimensionally stable, electrically insulating components.",categoryId:"cat-polymers",attributes:[{label:"Service temperature",value:"Illustrative 240 °C"},{label:"Tensile modulus",value:"Demo 3.6 GPa"},{label:"Density",value:"Demo 1.31 g/cm³"},{label:"Moisture response",value:"Illustrative low uptake"},{label:"Supply forms",value:"Rod · plate · molded"}],applications:["Electrical insulation","Thermal fixtures","Precision wear components"],cta:{id:"materials-px-view",label:"Review PX-620 evidence",href:`${materialsBase}/products/therma-px-620/`,intent:"view_product"}},
    { id:"grade-aerion-a7",slug:"aerion-a7-58",name:"AERION / A7-58",modelNumber:"A7-58 DEMO GRADE",shortDescription:"A fictional lightweight alloy grade balancing machinability, specific strength and protected-service durability.",categoryId:"cat-alloys",attributes:[{label:"Yield strength",value:"Illustrative 410 MPa"},{label:"Density",value:"Demo 2.72 g/cm³"},{label:"Elongation",value:"Demo 11%"},{label:"Process routes",value:"Plate · extrusion · AM"},{label:"Surface options",value:"Illustrative conversion coat"}],applications:["Lightweight structures","Thermal frames","Precision housings"],cta:{id:"materials-a7-view",label:"Review A7-58 evidence",href:`${materialsBase}/products/aerion-a7-58/`,intent:"view_product"}},
    { id:"grade-cerava-c9",slug:"cerava-c9-94",name:"CERAVA / C9-94",modelNumber:"C9-94 DEMO GRADE",shortDescription:"A fictional technical ceramic grade for wear interfaces, electrical isolation and stable high-temperature geometry.",categoryId:"cat-ceramics",attributes:[{label:"Hardness",value:"Illustrative 14 GPa"},{label:"Flexural strength",value:"Demo 330 MPa"},{label:"Density",value:"Demo 3.78 g/cm³"},{label:"Electrical behavior",value:"Illustrative insulating"},{label:"Supply forms",value:"Disc · tile · finished part"}],applications:["Wear interfaces","Electrical isolation","High-temperature guides"],cta:{id:"materials-c9-view",label:"Review C9-94 evidence",href:`${materialsBase}/products/cerava-c9-94/`,intent:"view_product"}},
  ],
  applications: [
    { id:"app-thermal",slug:"thermal-exposure",name:"Thermal exposure",description:"Balance continuous temperature, thermal cycling, dimensional stability and joining constraints." },
    { id:"app-wear",slug:"wear-motion",name:"Wear & motion",description:"Frame load, counterface, speed, lubrication and acceptable wear before selecting a grade." },
    { id:"app-electrical",slug:"electrical-isolation",name:"Electrical isolation",description:"Connect dielectric need, temperature, geometry and environmental exposure to material evidence." },
  ],
  capabilities: [
    { id:"cap-selection",slug:"application-selection",name:"Application-led selection",description:"Translate environment, load and processing conditions into a reviewable candidate set.",metrics:[{label:"Demo method",value:"4 condition axes"}] },
    { id:"cap-testing",slug:"test-context",name:"Test-context review",description:"Keep units, conditioning, method and specimen orientation attached to every property.",metrics:[{label:"Demo records",value:"Method-aware"}] },
    { id:"cap-sampling",slug:"sample-handoff",name:"Sample & validation handoff",description:"Carry target conditions and unresolved risks into sample and technical-support requests.",metrics:[{label:"Demo handoff",value:"Context retained"}] },
  ],
  certifications: [
    { id:"cert-rohs",name:"Example restricted-substance record",scope:"Demonstration only — no RoHS or other material compliance is claimed",demoOnly:true },
    { id:"cert-reach",name:"Example substance-declaration record",scope:"Illustrative document structure without a verified supplier declaration",demoOnly:true },
    { id:"cert-test",name:"Example test-method record",scope:"No laboratory accreditation, test result or certification is claimed",demoOnly:true },
  ],
  faqs: [
    { id:"faq-01",question:"Are these commercially available grades?",answer:"No. Every grade name, property, test record and supply form is fictional and exists only to demonstrate the selection experience." },
    { id:"faq-02",question:"Does a sample request go anywhere?",answer:"No. The static preview intercepts submission locally and creates no lead, contact, sample order or email." },
  ],
  rfqFields: [
    { id:"application",label:"Application",type:"text",required:true,placeholder:"Example: electrically isolated wear guide",forgeBaseField:"custom_fields.application" },
    { id:"environment",label:"Primary environment",type:"select",required:true,options:["Elevated temperature","Wear / motion","Electrical isolation","Chemical exposure"],forgeBaseField:"custom_fields.environment" },
    { id:"form",label:"Preferred supply form",type:"select",required:true,options:["Rod / plate","Sheet / extrusion","Machined component","Test coupon / sample"],forgeBaseField:"custom_fields.supply_form" },
    { id:"name",label:"Name",type:"text",required:true,placeholder:"Your name",forgeBaseField:"full_name" },
    { id:"email",label:"Work email",type:"email",required:true,placeholder:"name@company.com",forgeBaseField:"email" },
    { id:"company",label:"Company",type:"text",required:true,placeholder:"Company name",forgeBaseField:"company_name" },
    { id:"message",label:"Known conditions",type:"textarea",required:true,placeholder:"Temperature, load, counterface, chemical exposure and validation timing",forgeBaseField:"message" },
  ],
};

export const materialResources = [
  {code:"TDS-PX620",type:"Technical data concept",title:"THERMA / PX-620 property record",revision:"Demo Rev A",note:"Includes illustrative values only; no downloadable approved file."},
  {code:"TDS-A758",type:"Technical data concept",title:"AERION / A7-58 property record",revision:"Demo Rev B",note:"Shows method, condition and orientation placeholders."},
  {code:"SDS-C994",type:"Safety document concept",title:"CERAVA / C9-94 handling record",revision:"Demo Rev A",note:"Demonstrates controlled SDS placement without a real safety claim."},
] as const;

export const evidenceAxes = [
  {key:"thermal",label:"Thermal",hint:"Continuous heat, cycling and dimensional response"},
  {key:"mechanical",label:"Mechanical",hint:"Load, stiffness, impact and fatigue context"},
  {key:"environment",label:"Environment",hint:"Wear, chemical, moisture and electrical exposure"},
  {key:"process",label:"Process",hint:"Stock form, machining, molding and joining constraints"},
] as const;
