"""Standalone NanoFat for Joint Pain page content and schema helpers."""

import json
import re


FAQS = [
    (
        "What is NanoFat for joint pain?",
        "NanoFat is a mechanically processed fat-derived preparation being researched for its possible role in managing joint pain, particularly symptoms associated with knee osteoarthritis.",
    ),
    (
        "Does NanoFat work for knee osteoarthritis?",
        "Some early studies report improvements in pain and function, but larger high-quality clinical trials are required before its effectiveness can be considered established.",
    ),
    (
        "Can NanoFat regenerate knee cartilage?",
        "Reliable regeneration of damaged knee cartilage has not been demonstrated in clinical practice. Cartilage-related effects remain an area of research.",
    ),
    (
        "Is NanoFat a stem cell treatment?",
        "Not necessarily. NanoFat is a mechanically processed adipose tissue preparation and should not be described as identical to purified stem cell therapy.",
    ),
    (
        "Is NanoFat treatment non-surgical?",
        "Joint administration may involve an injection rather than open joint surgery, but collection of adipose tissue is an invasive procedure.",
    ),
    (
        "Is NanoFat treatment safe?",
        "Potential risks include pain, swelling, infection, bleeding and fat harvesting complications. Long-term safety requires further investigation.",
    ),
    (
        "How long does NanoFat treatment last?",
        "There is no established duration of benefit. Reported outcomes vary between studies and individuals.",
    ),
    (
        "Is NanoFat better than PRP?",
        "Available research does not establish that NanoFat is consistently superior to PRP for knee osteoarthritis.",
    ),
    (
        "Can NanoFat avoid knee replacement surgery?",
        "There is insufficient evidence that NanoFat can reliably prevent knee replacement surgery.",
    ),
    (
        "Who is eligible for NanoFat therapy?",
        "Eligibility depends on the patient's diagnosis, medical history, joint condition and the specific authorized treatment or research protocol.",
    ),
    (
        "Is NanoFat suitable for elderly patients?",
        "Suitability depends on overall health, procedural risk, severity of joint disease and clinical eligibility rather than age alone.",
    ),
    (
        "Can NanoFat permanently cure joint pain?",
        "No permanent cure has been established. Joint pain has many causes, and NanoFat has not been proven to permanently reverse osteoarthritis.",
    ),
    (
        "What is the cost of NanoFat treatment?",
        "Costs depend on the clinical protocol, facility, procedure and follow-up. Patients should request an estimate only after confirming availability and eligibility.",
    ),
    (
        "Is NanoFat available at Bankers Vascular Hospital?",
        "Contact the hospital to confirm whether NanoFat is offered under an appropriate clinical protocol. Patients can also request an appointment for knee pain evaluation and discussion of available treatments.",
    ),
]


PAGE_HTML = r'''
<main class="main-wrapper nanofat-page">
  <section class="nanofat-hero" aria-labelledby="nanofat-page-title">
    <div class="nanofat-hero-copy">
      <p class="nanofat-eyebrow">Diseases &amp; Treatments</p>
      <h1 id="nanofat-page-title">NanoFat for Joint Pain</h1>
      <p class="nanofat-hero-subtitle">Understanding an Emerging Fat-Derived Approach for Knee Osteoarthritis</p>
      <nav class="nanofat-breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a><span aria-hidden="true">→</span>
        <a href="/departments">Diseases &amp; Treatments</a><span aria-hidden="true">→</span>
        <span aria-current="page">NanoFat for Joint Pain</span>
      </nav>
    </div>
    <div class="nanofat-hero-media">
      <img src="/images/nanofat-joint-pain-hero.png" width="1672" height="940" loading="eager" fetchpriority="high" alt="Anatomical illustration of the human knee joint for NanoFat joint pain treatment information">
    </div>
  </section>

  <div class="nanofat-page-body">
    <aside class="nanofat-disclaimer nanofat-disclaimer--top" role="note">
      <strong>Important:</strong> NanoFat is an emerging approach under clinical investigation. It is not established as a cure for osteoarthritis or a reliable method of rebuilding damaged cartilage.
    </aside>

    <div class="nanofat-layout">
      <div class="nanofat-article-column">
        <aside class="nanofat-toc" aria-label="On this page">
          <p class="nanofat-toc-title">On this page</p>
          <a href="#what-is-nanofat">What is NanoFat?</a>
          <a href="#understanding-osteoarthritis">Joint pain and osteoarthritis</a>
          <a href="#how-nanofat-works">How it is being studied</a>
          <a href="#potential-benefits">Potential benefits</a>
          <a href="#who-may-be-considered">Who may be considered?</a>
          <a href="#nanofat-procedure">Procedure overview</a>
          <a href="#risks-limitations">Risks and limitations</a>
          <a href="#nanofat-vs-prp">NanoFat vs PRP</a>
          <a href="#clinical-research">Clinical research</a>
          <a href="#nanofat-faq">FAQs</a>
        </aside>

      <article class="nanofat-article">
        <section class="nanofat-section nanofat-intro" aria-labelledby="nanofat-overview-heading">
          <p class="nanofat-kicker">Patient education</p>
          <h2 id="nanofat-overview-heading">Understanding an Emerging Fat-Derived Approach for Knee Osteoarthritis</h2>
          <p>Joint pain can make simple everyday activities such as walking, climbing stairs, sitting, standing and exercising difficult. Persistent discomfort can interfere with mobility, independence and overall quality of life.</p>
          <p>Knee osteoarthritis is one of the most common causes of chronic joint pain. It develops through changes in cartilage, bone and other structures within the joint, often resulting in pain, stiffness and reduced movement.</p>
          <p>NanoFat is an emerging fat-derived treatment approach being investigated for its potential role in managing osteoarthritis symptoms.</p>
          <p>Researchers are studying whether specially processed adipose tissue may influence joint inflammation and improve pain-related functional outcomes in selected patients.</p>
          <p>Although early research has reported encouraging results, NanoFat has not been established as a cure for osteoarthritis or a reliable method of regenerating damaged cartilage.</p>
          <p>At Bankers Vascular Hospital, patients can seek an evaluation for knee pain and discuss appropriate treatment options based on their individual clinical needs.</p>
        </section>

        <section class="nanofat-section" id="what-is-nanofat" aria-labelledby="what-is-nanofat-heading">
          <h2 id="what-is-nanofat-heading">What Is NanoFat for Joint Pain?</h2>
          <p>NanoFat refers to a preparation made by mechanically processing adipose tissue, commonly known as body fat.</p>
          <p>The preparation is generally obtained from a patient's own body and processed according to a specific clinical or research protocol.</p>
          <p>Fat tissue contains various structural and biologically active components that researchers are investigating for their potential effects on tissue responses and inflammation.</p>
          <p>NanoFat and other processed adipose-tissue preparations are being studied in regenerative medicine, including research involving osteoarthritis.</p>
          <p>However, NanoFat should not automatically be described as stem cell therapy. The cellular composition and biological properties can differ significantly depending on the preparation method.</p>
          <p>In joint-related research, NanoFat is most commonly discussed in connection with knee osteoarthritis, although other potential applications continue to be investigated.</p>
          <p>The effectiveness and safety of this approach have not been conclusively established through large, long-term clinical trials.</p>
        </section>

        <section class="nanofat-section" id="understanding-osteoarthritis" aria-labelledby="understanding-osteoarthritis-heading">
          <h2 id="understanding-osteoarthritis-heading">Understanding Joint Pain and Osteoarthritis</h2>
          <p>Osteoarthritis is a degenerative joint condition involving progressive changes in joint cartilage, underlying bone and surrounding tissues.</p>
          <p>Healthy cartilage acts as a smooth protective surface that helps joints move with minimal friction.</p>
          <p>When osteoarthritis develops, structural and inflammatory changes can contribute to discomfort, swelling, stiffness and difficulty moving.</p>
          <h3>Common Symptoms of Knee Osteoarthritis</h3>
          <p>Patients may experience:</p>
          <ul>
            <li>Knee pain during walking or standing</li>
            <li>Morning stiffness or stiffness after resting</li>
            <li>Difficulty climbing stairs</li>
            <li>Swelling around the knee</li>
            <li>Reduced flexibility</li>
            <li>Joint tenderness</li>
            <li>Grinding or clicking sensations</li>
            <li>Difficulty bending or straightening the knee</li>
            <li>Reduced walking tolerance</li>
          </ul>
          <p>Not all knee pain is caused by osteoarthritis. Ligament injuries, tendon problems, inflammatory conditions and other disorders may produce similar symptoms.</p>
          <p>An accurate diagnosis is essential before considering treatment.</p>
        </section>

        <section class="nanofat-section" id="how-nanofat-works" aria-labelledby="how-nanofat-works-heading">
          <h2 id="how-nanofat-works-heading">How Does NanoFat Work for Joint Pain?</h2>
          <p>Researchers are investigating several possible biological mechanisms associated with processed adipose tissue.</p>
          <h3>1. Inflammation-Related Responses</h3>
          <p>Inflammation plays an important role in osteoarthritis symptoms.</p>
          <p>Components of processed adipose tissue are being studied for possible effects on inflammatory signaling and local tissue responses.</p>
          <p>These effects remain under clinical investigation.</p>
          <h3>2. Joint Tissue Environment</h3>
          <p>NanoFat preparations contain fat-derived structural and biological components.</p>
          <p>Researchers are exploring whether these components may interact with the joint environment and influence cellular processes.</p>
          <h3>3. Pain and Functional Outcomes</h3>
          <p>Some early clinical studies involving fat-derived preparations have reported improvements in pain scores and physical function.</p>
          <p>However, the results are not consistent enough to predict outcomes for individual patients.</p>
          <h3>4. Cartilage-Related Research</h3>
          <p>Laboratory and clinical researchers are studying whether fat-derived preparations may influence cartilage-related biological processes.</p>
          <p>Importantly, reliable regeneration of damaged human knee cartilage has not been demonstrated.</p>
          <p>NanoFat must not be presented as a proven cartilage rebuilding treatment.</p>
        </section>

        <section class="nanofat-section" id="potential-benefits" aria-labelledby="potential-benefits-heading">
          <h2 id="potential-benefits-heading">Potential Benefits of NanoFat Being Investigated</h2>
          <p>Researchers are evaluating several potential outcomes.</p>
          <h3>Joint Pain Reduction</h3>
          <p>Some preliminary studies report reductions in patient-reported joint discomfort after fat-derived injections.</p>
          <p>The size and duration of these effects remain uncertain.</p>
          <h3>Improved Joint Mobility</h3>
          <p>Certain studies suggest that patients may experience improvements in mobility and daily function.</p>
          <p>These findings require confirmation through larger comparative trials.</p>
          <h3>Use of Autologous Tissue</h3>
          <p>Some NanoFat protocols use the patient's own adipose tissue.</p>
          <p>Although this approach uses autologous material, it does not eliminate procedural risks or guarantee treatment effectiveness.</p>
          <h3>Injection-Based Administration</h3>
          <p>NanoFat may be delivered using an intra-articular injection under an appropriate clinical or research protocol.</p>
          <p>However, obtaining the fat tissue involves an invasive harvesting procedure.</p>
          <h3>Investigation of New Osteoarthritis Treatments</h3>
          <p>Ongoing research may contribute to better understanding of biological approaches to joint pain management.</p>
          <p>Patients should understand that these benefits are potential research outcomes, not assured clinical results.</p>
        </section>

        <section class="nanofat-section" id="who-may-be-considered" aria-labelledby="who-may-be-considered-heading">
          <h2 id="who-may-be-considered-heading">Who May Be Considered for NanoFat Evaluation?</h2>
          <p>The suitability of an investigational fat-derived treatment depends on the patient's diagnosis, medical condition and the specific authorized clinical protocol.</p>
          <p>A specialist may review the following factors:</p>
          <ul>
            <li>Confirmed knee osteoarthritis</li>
            <li>Persistent symptoms affecting daily activities</li>
            <li>Previous response to conservative treatment</li>
            <li>Joint imaging findings</li>
            <li>Severity of joint degeneration</li>
            <li>General health and existing medical conditions</li>
            <li>Potential procedural risks</li>
            <li>Regulatory and clinical eligibility requirements</li>
          </ul>
          <p>Patients with advanced joint deformity, significant instability, infection or certain medical conditions may require other forms of treatment.</p>
          <p>There is no universal eligibility standard for NanoFat therapy.</p>
        </section>

        <section class="nanofat-section" id="nanofat-procedure" aria-labelledby="nanofat-procedure-heading">
          <h2 id="nanofat-procedure-heading">Step-by-Step NanoFat Procedure</h2>
          <p>Different clinical studies use different collection, processing and administration methods.</p>
          <p>The following overview describes general steps reported in fat-derived joint treatment research.</p>
          <h3>Step 1 — Clinical Assessment</h3>
          <p>The doctor reviews the patient's symptoms, medical history, previous treatment and functional limitations.</p>
          <p>An examination is performed, and imaging may be recommended where appropriate.</p>
          <h3>Step 2 — Fat Tissue Collection</h3>
          <p>In certain protocols, a small amount of adipose tissue is collected from a suitable body area using an invasive harvesting procedure.</p>
          <p>The technique and anesthesia requirements depend on the treatment protocol.</p>
          <h3>Step 3 — Tissue Processing</h3>
          <p>The collected adipose tissue undergoes mechanical processing.</p>
          <p>Different processing methods may produce different tissue preparations.</p>
          <h3>Step 4 — Joint Administration</h3>
          <p>Where appropriately authorized, the resulting preparation may be injected into the affected joint using a sterile technique.</p>
          <p>Imaging guidance may be used according to clinical requirements.</p>
          <h3>Step 5 — Post-Procedure Monitoring</h3>
          <p>The patient is assessed after the procedure and receives instructions concerning symptoms, wound care, physical activity and follow-up.</p>
          <h3>Step 6 — Follow-Up and Rehabilitation</h3>
          <p>Ongoing clinical review helps assess pain, mobility, complications and functional progress.</p>
          <p>Physiotherapy or a rehabilitation program may be recommended as part of continued osteoarthritis management.</p>
        </section>

        <section class="nanofat-section" aria-labelledby="pain-heading">
          <h2 id="pain-heading">Is NanoFat Treatment Painful?</h2>
          <p>Discomfort can occur during adipose tissue collection and after injection.</p>
          <p>Anesthesia may be used during tissue harvesting to reduce procedural discomfort.</p>
          <p>Patients may experience temporary soreness, swelling or bruising around the collection site or treated joint.</p>
          <p>The amount of discomfort varies according to the procedure and individual patient factors.</p>
          <p>Patients should discuss anesthesia, pain management and potential complications with their treating specialist.</p>
        </section>

        <section class="nanofat-section" aria-labelledby="recovery-heading">
          <h2 id="recovery-heading">Recovery After NanoFat Joint Treatment</h2>
          <p>Recovery varies depending on the harvesting technique, joint condition and medical history.</p>
          <p>Possible short-term effects include:</p>
          <ul>
            <li>Temporary joint soreness</li>
            <li>Mild swelling</li>
            <li>Tenderness near the collection area</li>
            <li>Bruising</li>
            <li>Temporary activity restrictions</li>
          </ul>
          <p>The healthcare team should provide individualized recovery and follow-up instructions.</p>
          <p>There is currently no universally established recovery timeline for NanoFat treatment of osteoarthritis.</p>
        </section>

        <section class="nanofat-section" id="risks-limitations" aria-labelledby="risks-limitations-heading">
          <h2 id="risks-limitations-heading">Risks and Limitations of NanoFat Treatment</h2>
          <p>All invasive procedures carry potential risks.</p>
          <p>Possible complications include:</p>
          <ul>
            <li>Pain or swelling</li>
            <li>Infection</li>
            <li>Bleeding</li>
            <li>Bruising or hematoma</li>
            <li>Fat harvesting complications</li>
            <li>Tissue injury</li>
            <li>Anesthesia-related complications</li>
            <li>Persistent symptoms</li>
            <li>No meaningful improvement in pain or function</li>
          </ul>
          <p>Long-term safety and effectiveness remain areas of active clinical research.</p>
          <p>Patients should understand that NanoFat is an emerging approach and may not be appropriate or available outside an authorized clinical setting.</p>
        </section>

        <section class="nanofat-section" id="nanofat-vs-prp" aria-labelledby="nanofat-vs-prp-heading">
          <h2 id="nanofat-vs-prp-heading">NanoFat vs PRP vs Conventional Knee Osteoarthritis Treatments</h2>
          <p>Osteoarthritis management includes several treatment approaches.</p>
          <h3>Physiotherapy and Exercise</h3>
          <p>Structured exercise, strengthening and physical rehabilitation are established components of knee osteoarthritis management.</p>
          <p>These interventions can improve function and help manage symptoms.</p>
          <h3>Medication</h3>
          <p>Depending on the patient's condition, doctors may recommend appropriate pain-relieving or anti-inflammatory medication.</p>
          <p>Medication decisions should consider medical history, potential side effects and individual needs.</p>
          <h3>Platelet-Rich Plasma (PRP)</h3>
          <p>PRP is prepared from a patient's blood and contains concentrated platelets.</p>
          <p>Its use in knee osteoarthritis has been investigated, although evidence and clinical recommendations vary. Learn more about <a href="/treatment/platelet-rich-plasma">PRP treatment information</a>.</p>
          <h3>NanoFat</h3>
          <p>NanoFat uses processed adipose tissue and is being investigated for potential effects on osteoarthritis symptoms.</p>
          <p>There is insufficient high-quality comparative evidence to establish that NanoFat is consistently superior to PRP or other established options.</p>
          <h3>Knee Replacement Surgery</h3>
          <p>Knee replacement may be considered for patients with severe osteoarthritis, persistent pain and significant functional limitations despite appropriate treatment.</p>
          <p>The decision depends on clinical assessment and patient preferences.</p>
        </section>

        <section class="nanofat-section" aria-labelledby="replacement-heading">
          <h2 id="replacement-heading">Can NanoFat Prevent Knee Replacement Surgery?</h2>
          <p>There is currently insufficient evidence that NanoFat can reliably prevent or delay knee replacement surgery.</p>
          <p>Many patients with knee osteoarthritis can manage symptoms through appropriate non-operative treatment.</p>
          <p>However, some individuals with advanced disease may benefit from surgical treatment.</p>
          <p>NanoFat should not be promoted as a guaranteed alternative to knee replacement.</p>
          <p>An individualized clinical assessment helps determine the appropriate treatment pathway.</p>
        </section>

        <section class="nanofat-section nanofat-research" id="clinical-research" aria-labelledby="clinical-research-heading">
          <h2 id="clinical-research-heading">What Does Clinical Research Say About NanoFat?</h2>
          <p>Research into adipose-derived treatments for osteoarthritis has expanded in recent years.</p>
          <p>Early studies and systematic reviews have investigated possible improvements in pain, knee function and patient-reported outcomes.</p>
          <p>However, the available evidence has important limitations.</p>
          <p>These include:</p>
          <ul>
            <li>Small study populations</li>
            <li>Different tissue processing techniques</li>
            <li>Differences in injection protocols</li>
            <li>Limited long-term follow-up</li>
            <li>Variation in patient characteristics</li>
            <li>Inconsistent comparison groups</li>
          </ul>
          <p>Larger randomized controlled trials are necessary to determine which patients, if any, benefit most and how the treatment compares with established osteoarthritis management.</p>
          <p>Researchers must also clarify long-term safety, standardization and regulatory considerations.</p>
          <div class="nanofat-references">
            <h3>Selected peer-reviewed references</h3>
            <ol>
              <li>Hohmann E, Keough N, Frank RM, Rodeo S. <a href="https://pubmed.ncbi.nlm.nih.gov/38467171/" target="_blank" rel="noopener noreferrer">Micro-Fragmented Adipose Tissue Demonstrates Comparable Clinical Efficacy to Other Orthobiologic Injections in Treating Symptomatic Knee Osteoarthritis</a>. Arthroscopy. 2025;41(2):418-441.e14.</li>
              <li>Ye X, Shen Z, Li X, et al. <a href="https://pubmed.ncbi.nlm.nih.gov/39851028/" target="_blank" rel="noopener noreferrer">Microfragmented adipose tissue versus platelet-rich plasma in the treatment of knee osteoarthritis: a systematic review and meta-analysis</a>. Acta Orthop Belg. 2024;90(3):549-558.</li>
              <li>Di Matteo B, et al. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC10780289/" target="_blank" rel="noopener noreferrer">Adipose Tissue-Derived Minimally Manipulated Products versus Platelet-Rich Plasma for the Treatment of Knee Osteoarthritis</a>. 2023 systematic review of clinical evidence and meta-analysis.</li>
            </ol>
          </div>
        </section>

        <section class="nanofat-section" aria-labelledby="why-bankers-heading">
          <h2 id="why-bankers-heading">Why Choose Bankers Vascular Hospital for Joint Pain Evaluation?</h2>
          <p>Bankers Vascular Hospital focuses on patient assessment, education and appropriate treatment planning.</p>
          <h3>Individualized Patient Evaluation</h3>
          <p>Each patient's joint symptoms, medical history and mobility limitations are considered when discussing treatment.</p>
          <h3>Understanding Minimally Invasive Options</h3>
          <p>Patients can discuss suitable minimally invasive approaches alongside other established treatment pathways.</p>
          <h3>Clear Medical Guidance</h3>
          <p>Our goal is to help patients understand available options, possible benefits, procedural risks and clinical limitations.</p>
          <h3>Ahmedabad and Vadodara Consultations</h3>
          <p>Patients in Ahmedabad and Vadodara can contact Bankers Vascular Hospital for information about joint pain evaluation and relevant specialist services.</p>
          <p>NanoFat treatment availability must be independently confirmed before it is advertised or offered.</p>
        </section>

        <section class="nanofat-section nanofat-faq-section" id="nanofat-faq" aria-labelledby="nanofat-faq-heading">
          <p class="nanofat-kicker">Questions patients ask</p>
          <h2 id="nanofat-faq-heading">Frequently Asked Questions</h2>
          <div class="faq-wrapper nanofat-faq-list">
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">What is NanoFat for joint pain?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">NanoFat is a mechanically processed fat-derived preparation being researched for its possible role in managing joint pain, particularly symptoms associated with knee osteoarthritis.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Does NanoFat work for knee osteoarthritis?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Some early studies report improvements in pain and function, but larger high-quality clinical trials are required before its effectiveness can be considered established.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Can NanoFat regenerate knee cartilage?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Reliable regeneration of damaged knee cartilage has not been demonstrated in clinical practice. Cartilage-related effects remain an area of research.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Is NanoFat a stem cell treatment?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Not necessarily. NanoFat is a mechanically processed adipose tissue preparation and should not be described as identical to purified stem cell therapy.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Is NanoFat treatment non-surgical?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Joint administration may involve an injection rather than open joint surgery, but collection of adipose tissue is an invasive procedure.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Is NanoFat treatment safe?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Potential risks include pain, swelling, infection, bleeding and fat harvesting complications. Long-term safety requires further investigation.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">How long does NanoFat treatment last?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">There is no established duration of benefit. Reported outcomes vary between studies and individuals.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Is NanoFat better than PRP?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Available research does not establish that NanoFat is consistently superior to PRP for knee osteoarthritis.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Can NanoFat avoid knee replacement surgery?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">There is insufficient evidence that NanoFat can reliably prevent knee replacement surgery.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Who is eligible for NanoFat therapy?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Eligibility depends on the patient's diagnosis, medical history, joint condition and the specific authorized treatment or research protocol.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Is NanoFat suitable for elderly patients?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Suitability depends on overall health, procedural risk, severity of joint disease and clinical eligibility rather than age alone.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Can NanoFat permanently cure joint pain?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">No permanent cure has been established. Joint pain has many causes, and NanoFat has not been proven to permanently reverse osteoarthritis.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">What is the cost of NanoFat treatment?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Costs depend on the clinical protocol, facility, procedure and follow-up. Patients should request an estimate only after confirming availability and eligibility.</p></div></details>
            <details class="accordion-container nanofat-faq-item"><summary class="accordion-toggle nanofat-faq-summary">Is NanoFat available at Bankers Vascular Hospital?<span class="accordion-dopdown-icon" aria-hidden="true"></span></summary><div class="accordion-dropdown-body faq nanofat-faq-answer"><p class="accordion-dropdown-text faq">Contact the hospital to confirm whether NanoFat is offered under an appropriate clinical protocol. Patients can also request an appointment for knee pain evaluation and discussion of available treatments.</p></div></details>
          </div>
        </section>
      </article>
      </div>

      <aside class="nanofat-reference-sidebar" aria-labelledby="nanofat-sidebar-heading">
        <div class="nanofat-reference-sidebar-heading" id="nanofat-sidebar-heading">Book An Appointment</div>
        <div class="nanofat-sidebar-form-block w-form">
          <form id="nanofat-sidebar-form" name="nanofat-sidebar-form" data-name="NanoFat Appointment" method="post" action="/api/contact" class="nanofat-sidebar-form">
            <label>Patient Name<input class="input-field contact w-input" name="Name" type="text" placeholder="Your name" required></label>
            <label>Mobile Number<input class="input-field contact w-input" name="Phone-Number" type="tel" placeholder="Your mobile number" required></label>
            <button type="submit" class="outline-button w-button">Book Appointment Now</button>
          </form>
          <div class="success-message-2 w-form-done"><div class="text-block-37">Thank you! Your request has been received.</div><a href="https://wa.me/919909908428" target="_blank" rel="noopener noreferrer" class="button w-button">Talk on WhatsApp</a></div>
          <div class="w-form-fail"><div>We could not send your request. Please call the hospital directly.</div></div>
        </div>
        <div class="nanofat-sidebar-contact">
          <p>Call us for knee pain evaluation and treatment guidance.</p>
          <a href="tel:+919909908428">+91 99099 08428</a>
          <a href="https://wa.me/919909908428" target="_blank" rel="noopener noreferrer">Chat on WhatsApp</a>
        </div>
      </aside>
    </div>

    <section class="nanofat-appointment" id="nanofat-appointment" aria-labelledby="nanofat-appointment-heading">
      <div class="nanofat-appointment-intro">
        <p class="nanofat-kicker">Personalized guidance</p>
        <h2 id="nanofat-appointment-heading">Consult Our Specialists for Joint Pain</h2>
        <p>Experiencing persistent knee pain or joint stiffness? Contact Bankers Vascular Hospital for an evaluation and personalized guidance on appropriate treatment options.</p>
        <div class="nanofat-quick-actions">
          <a class="button w-button" href="tel:+919909908428">Call Ahmedabad</a>
          <a class="nanofat-whatsapp" href="https://wa.me/919909908428" target="_blank" rel="noopener noreferrer">WhatsApp the hospital</a>
        </div>
      </div>
      <div class="nanofat-locations">
        <div class="nanofat-location-card">
          <h3>Bankers Vascular Hospital — Ahmedabad</h3>
          <a href="tel:+919909908428">+91 99099 08428</a>
          <a href="tel:+919909903449">+91 99099 03449</a>
        </div>
        <div class="nanofat-location-card">
          <h3>Bankers Vascular Hospital — Vadodara</h3>
          <p>201, Ignite Complex, Above Meera Eye Hospital, Opp. Agrawal Motors, Near Urmi Char Rasta, Akota, Vadodara – 390020</p>
          <a href="tel:+916358156753">+91 63581 56753</a>
          <a href="tel:+916358156749">+91 63581 56749</a>
        </div>
      </div>
      <div class="contact-form-block w-form nanofat-form-block">
        <form id="nanofat-appointment-form" name="nanofat-appointment-form" data-name="Joint Pain Consultation" method="post" action="/api/contact" class="contact-form nanofat-appointment-form">
          <div class="nanofat-form-grid">
            <label>Patient Name<input class="input-field contact w-input" name="Name" type="text" placeholder="Patient name" required></label>
            <label>Mobile Number<input class="input-field contact w-input" name="Phone-Number" type="tel" placeholder="Mobile number" required></label>
            <label>City<select class="input-field contact w-input" name="City"><option value="">Select city</option><option>Ahmedabad</option><option>Vadodara</option><option>Other</option></select></label>
            <label>Preferred Hospital<select class="input-field contact w-input" name="Preferred Hospital"><option value="">Select hospital</option><option>Ahmedabad</option><option>Vadodara</option></select></label>
            <label class="nanofat-form-wide">Joint Pain / Medical Concern<input class="input-field contact w-input" name="Concern" type="text" placeholder="Tell us briefly what you would like to discuss"></label>
            <label class="nanofat-form-wide">Message<textarea class="input-field contact w-input nanofat-message" name="Message" rows="4" placeholder="Message"></textarea></label>
          </div>
          <button type="submit" class="outline-button w-button">Request an evaluation</button>
        </form>
        <div class="success-message-2 w-form-done"><div class="text-block-37">Thank you! Your request has been received.</div><a href="https://wa.me/919909908428" target="_blank" rel="noopener noreferrer" class="button w-button">Talk on WhatsApp</a></div>
        <div class="w-form-fail"><div>We could not send your request. Please call the hospital directly.</div></div>
      </div>
    </section>

    <section class="nanofat-emergency" aria-labelledby="nanofat-emergency-heading">
      <div class="nanofat-emergency-copy">
        <p class="nanofat-kicker">Need help with knee pain?</p>
        <h2 id="nanofat-emergency-heading">Looking For The Best Medical Solutions?</h2>
        <p>Speak with the Bankers Vascular Hospital team about persistent knee pain, mobility concerns and the right next step for your care.</p>
        <div class="nanofat-quick-actions">
          <a class="button w-button" href="https://wa.me/919909908428" target="_blank" rel="noopener noreferrer">Chat on WhatsApp</a>
          <a class="nanofat-whatsapp" href="tel:+919909908428">Call Our Helpline 24/7</a>
        </div>
      </div>
      <div class="nanofat-emergency-media">
        <img src="/images/nanofat-joint-pain-card.png" width="1200" height="800" loading="lazy" alt="Patient education illustration for joint pain care">
      </div>
    </section>

    <p class="nanofat-disclaimer nanofat-disclaimer--bottom">This content is intended for general educational purposes only and does not replace professional medical advice. NanoFat is an emerging treatment approach. Its clinical effectiveness, safety, regulatory status and availability may vary. Treatment decisions should be made after consultation with a qualified medical professional.</p>
  </div>
</main>
'''


def customise_shell(html):
    """Replace the department template's CMS content with the NanoFat page."""
    # The department reference shell already places navigation directly inside
    # the page wrapper. Keep a fallback for older shells that nest the header
    # inside the page-specific content.
    has_top_level_header = re.search(
        r'<main class="page-wrapper">\s*<header\b', html, flags=re.S
    )
    header_match = re.search(
        r'<header class="navbar-two section-4">.*?</header>',
        html,
        flags=re.S,
    ) if not has_top_level_header else None
    header = header_match.group(0) if header_match else ""
    html = re.sub(r'\s*<h6>.*?</h6>', '', html, count=1, flags=re.S)
    html = re.sub(
        r'<main class="main-wrapper">.*?</main>',
        PAGE_HTML.strip(),
        html,
        count=1,
        flags=re.S,
    )
    if header:
        html = html.replace(
            '<main class="page-wrapper">',
            '<main class="page-wrapper">\n    ' + header,
            1,
        )
    # The contact-page template marks its CTA as current; this page should not.
    html = html.replace(
        'href="/contact-us" aria-current="page" class="button w-button w--current"',
        'href="/contact-us" class="button w-button"',
    )
    return html


def add_schema(html, site_url):
    """Add medical-page and visible FAQ structured data."""
    canonical = site_url + "/nanofat-for-joint-pain"
    faq = {
        "@type": "FAQPage",
        "@id": canonical + "#faq",
        "url": canonical,
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in FAQS
        ],
    }
    medical = {
        "@type": "MedicalWebPage",
        "@id": canonical + "#medical-webpage",
        "url": canonical,
        "name": "NanoFat for Joint Pain | Knee Osteoarthritis Treatment",
        "description": "Learn about NanoFat for joint pain and knee osteoarthritis, including how it works, potential benefits, procedure, risks and current research.",
        "inLanguage": "en-IN",
        "medicalAudience": {"@type": "MedicalAudience", "audienceType": "Patient"},
        "about": {"@type": "MedicalCondition", "name": "Knee osteoarthritis and joint pain"},
    }
    tag = '  <script type="application/ld+json">%s</script>\n</head>' % json.dumps(
        {"@context": "https://schema.org", "@graph": [medical, faq]},
        ensure_ascii=False,
    )
    return html.replace("</head>", tag, 1)
