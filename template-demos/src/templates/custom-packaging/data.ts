import type { TemplateDemoData } from "@/contracts/forgebase";

export const packagingBase="/templates/custom-packaging";
export const customPackagingData:TemplateDemoData={
 site:{companyName:"Tuckform Packaging",legalNotice:"Demonstration company — not a registered packaging manufacturer, printer or converter",tagline:"From flat idea to repeatable pack.",description:"A ForgeBase website template for custom packaging manufacturers and converters.",email:"packaging-demo@example.com",phone:"+00 000 000 000",location:"Demonstration production region",disclosure:{label:"Packaging Studio Preview",message:"All structures, materials, print capabilities, MOQs, timelines, sustainability statements and company details are illustrative."}},
 ctas:[
  {id:"packaging-nav-brief",label:"Build a packaging brief",href:`${packagingBase}/rfq/`,intent:"request_quote",variant:"primary"},
  {id:"packaging-configure",label:"Configure a pack",href:`${packagingBase}/rfq/`,intent:"request_quote",variant:"primary"},
  {id:"packaging-systems",label:"Explore packaging systems",href:`${packagingBase}/products/`,intent:"view_product",variant:"secondary"},
  {id:"packaging-sample",label:"Request a structural sample",href:`${packagingBase}/rfq/`,intent:"request_sample",variant:"text"},
  {id:"packaging-submit",label:"Prepare packaging brief",href:`${packagingBase}/rfq/`,intent:"request_quote",variant:"primary"},
 ],
 categories:[
  {id:"cat-mailer",slug:"corrugated-mailers",name:"Corrugated mailers",description:"Protective shipping structures balancing board grade, insert strategy and pack-out speed."},
  {id:"cat-carton",slug:"folding-cartons",name:"Folding cartons",description:"Printed paperboard structures connecting shelf presence, filling process and efficient flat shipment."},
  {id:"cat-rigid",slug:"rigid-boxes",name:"Rigid boxes",description:"Paper-wrapped presentation structures organized around fit, insert and repeatable assembly."},
 ],
 products:[
  {id:"pack-ship-s1",slug:"ship-s1-mailer",name:"SHIP / S1 MAILER",modelNumber:"S1 STRUCTURE / DEMO",shortDescription:"A fictional roll-end corrugated mailer system with a paper-based insert and configurable pack-out geometry.",categoryId:"cat-mailer",attributes:[{label:"Board",value:"Demo E-flute kraft"},{label:"Print",value:"Illustrative 2-color flexo"},{label:"Insert",value:"Molded paper / die-cut board"},{label:"MOQ",value:"Illustrative 1,000 units"},{label:"Sample",value:"Digital-cut prototype"}],applications:["E-commerce fulfilment","Industrial accessories","Subscription kits"],cta:{id:"packaging-s1-view",label:"Explore SHIP / S1",href:`${packagingBase}/products/ship-s1-mailer/`,intent:"view_product"}},
  {id:"pack-fold-f2",slug:"fold-f2-carton",name:"FOLD / F2 CARTON",modelNumber:"F2 STRUCTURE / DEMO",shortDescription:"A fictional straight-tuck folding-carton family with scalable graphics, compact shipment and filling-line context.",categoryId:"cat-carton",attributes:[{label:"Board",value:"Demo 400 gsm SBS"},{label:"Print",value:"Illustrative CMYK + spot"},{label:"Finish",value:"Demo matte aqueous"},{label:"MOQ",value:"Illustrative 3,000 units"},{label:"Sample",value:"Printed color mockup"}],applications:["Retail components","Health devices","Specialty consumables"],cta:{id:"packaging-f2-view",label:"Explore FOLD / F2",href:`${packagingBase}/products/fold-f2-carton/`,intent:"view_product"}},
  {id:"pack-present-r3",slug:"present-r3-rigid-box",name:"PRESENT / R3",modelNumber:"R3 STRUCTURE / DEMO",shortDescription:"A fictional lift-off rigid-box system with paper wrap and fitted fiber insert for controlled presentation.",categoryId:"cat-rigid",attributes:[{label:"Board",value:"Demo 1.8 mm grayboard"},{label:"Wrap",value:"Illustrative uncoated paper"},{label:"Insert",value:"Molded fiber tray"},{label:"MOQ",value:"Illustrative 2,000 units"},{label:"Sample",value:"White + printed prototype"}],applications:["Launch kits","Premium instruments","Presentation sets"],cta:{id:"packaging-r3-view",label:"Explore PRESENT / R3",href:`${packagingBase}/products/present-r3-rigid-box/`,intent:"view_product"}},
 ],
 applications:[
  {id:"app-transit",slug:"transit-protection",name:"Transit protection",description:"Connect product fragility, distribution path, insert retention and pack-out labor before choosing a shipper."},
  {id:"app-retail",slug:"retail-presentation",name:"Retail presentation",description:"Balance shelf geometry, print hierarchy, filling process and flat-pack efficiency."},
  {id:"app-launch",slug:"launch-kits",name:"Launch & presentation kits",description:"Coordinate component fit, opening sequence, kitting and repeatable assembly across a program."},
 ],
 capabilities:[
  {id:"cap-structure",slug:"structural-design",name:"Structural design",description:"Translate product dimensions, fragility and pack-out into a reviewable dieline and insert concept.",metrics:[{label:"Demo gate",value:"Dieline review"}]},
  {id:"cap-sampling",slug:"sampling-proofing",name:"Sampling & proofing",description:"Separate structural white samples, printed color mocks and production-ready approvals.",metrics:[{label:"Demo path",value:"White → color → approval"}]},
  {id:"cap-production",slug:"production-handoff",name:"Production handoff",description:"Carry approved structure, artwork, board, finish, quantity and packing instructions into repeat orders.",metrics:[{label:"Demo control",value:"Revision-aware"}]},
 ],
 certifications:[
  {id:"cert-fiber",name:"Example responsible-fiber record",scope:"Demonstration only — no FSC, PEFC or sourcing certification is claimed",demoOnly:true},
  {id:"cert-ink",name:"Example ink and coating declaration",scope:"Illustrative evidence structure without a verified formulation",demoOnly:true},
  {id:"cert-transit",name:"Example transit-test record",scope:"No ISTA test, performance result or laboratory certification is claimed",demoOnly:true},
 ],
 faqs:[
  {id:"faq-01",question:"Are the MOQs and lead times real?",answer:"No. Every quantity, material, process and timeline is fictional and exists only to demonstrate the configuration experience."},
  {id:"faq-02",question:"Will the packaging brief be sent?",answer:"No. The static preview keeps the interaction local and creates no quote, sample order, lead, contact record or email."},
 ],
 rfqFields:[
  {id:"style",label:"Packaging style",type:"select",required:true,options:["Corrugated mailer","Folding carton","Rigid box"],forgeBaseField:"custom_fields.pack_style"},
  {id:"dimensions",label:"Internal dimensions",type:"text",required:true,placeholder:"L × W × H mm",forgeBaseField:"custom_fields.dimensions"},
  {id:"material",label:"Material direction",type:"select",required:true,options:["Kraft corrugated","White corrugated","SBS paperboard","Paper-wrapped rigid board"],forgeBaseField:"custom_fields.material"},
  {id:"print",label:"Print coverage",type:"select",required:true,options:["No print / structural","1–2 spot colors","CMYK exterior","CMYK inside + outside"],forgeBaseField:"custom_fields.print"},
  {id:"quantity",label:"Initial quantity",type:"select",required:true,options:["1,000","2,500","5,000","10,000+"],forgeBaseField:"custom_fields.quantity"},
  {id:"name",label:"Name",type:"text",required:true,placeholder:"Your name",forgeBaseField:"full_name"},
  {id:"email",label:"Work email",type:"email",required:true,placeholder:"name@company.com",forgeBaseField:"email"},
  {id:"message",label:"Product and pack-out context",type:"textarea",required:true,placeholder:"Product weight, fragility, components, distribution and target launch",forgeBaseField:"message"},
 ],
};
export const productionSteps=[
 {code:"01",name:"Contain",text:"Define product envelope, orientation, protection and pack-out."},
 {code:"02",name:"Prototype",text:"Review structure before print, finish and volume assumptions."},
 {code:"03",name:"Approve",text:"Lock dieline, material, artwork and sample revision."},
 {code:"04",name:"Repeat",text:"Carry the approved pack specification into repeat production."},
] as const;
