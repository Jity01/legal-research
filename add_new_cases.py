"""
Script to add new cases from user input.
Collects cases and processes them all at once.
"""

import sys
import os
from typing import Dict, List
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_supabase_client, save_case
from strategy.case_analyzer import CaseAnalyzer
from strategy.citation_extractor import CitationExtractor
from process_cases_table import process_single_case
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store cases as they come in
cases_to_process: List[Dict] = []

def add_case(case_text: str, url: str = None) -> None:
    """Add a case to the processing queue"""
    cases_to_process.append({
        "text": case_text,
        "url": url
    })
    logger.info(f"Added case {len(cases_to_process)}/19")

def extract_case_info(case_text: str) -> Dict:
    """Extract basic case information from text"""
    case_info = {
        "case_name": "",
        "citation": "",
        "docket_number": "",
        "court_name": "",
        "court_type": "",
        "decision_date": None,
        "judges": "",
        "opinion_text": case_text,
        "source": "user_input",
        "source_url": None
    }
    
    # Extract case name (usually first line or after "v.")
    lines = case_text.split('\n')
    for line in lines[:10]:
        line = line.strip()
        if 'v.' in line or 'v ' in line:
            case_info["case_name"] = line.split('Court')[0].strip()
            break
    
    # Extract citation
    import re
    citation_match = re.search(r'Citations?:\s*([^\n]+)', case_text)
    if citation_match:
        case_info["citation"] = citation_match.group(1).strip()
    
    # Extract docket number
    docket_match = re.search(r'Docket Number:\s*([^\n]+)', case_text)
    if docket_match:
        case_info["docket_number"] = docket_match.group(1).strip()
    
    # Extract court
    court_match = re.search(r'Court of Appeals for the ([^\n]+)', case_text)
    if court_match:
        case_info["court_name"] = f"Court of Appeals for the {court_match.group(1).strip()}"
        case_info["court_type"] = "federal_appeals"
    
    # Extract judges
    judges_match = re.search(r'Judges:\s*([^\n]+)', case_text)
    if judges_match:
        case_info["judges"] = judges_match.group(1).strip()
    
    # Extract date
    date_match = re.search(r'(\w+\s+\d+,\s+\d{4})', case_text)
    if date_match:
        try:
            date_str = date_match.group(1)
            case_info["decision_date"] = datetime.strptime(date_str, "%B %d, %Y").date()
        except:
            pass
    
    return case_info

def process_all_cases():
    """Process all collected cases"""
    if len(cases_to_process) != 19:
        logger.error(f"Expected 19 cases, but only have {len(cases_to_process)}")
        return
    
    logger.info(f"Processing {len(cases_to_process)} cases...")
    
    client = get_supabase_client()
    analyzer = CaseAnalyzer()
    citation_extractor = CitationExtractor()
    
    success_count = 0
    error_count = 0
    
    for idx, case_data in enumerate(cases_to_process, 1):
        try:
            logger.info(f"Processing case {idx}/19...")
            
            # Extract case info
            case_info = extract_case_info(case_data["text"])
            if case_data.get("url"):
                case_info["source_url"] = case_data["url"]
            
            # Process the case
            success, error = process_single_case(
                case_info,
                analyzer,
                citation_extractor,
                client,
                force=True
            )
            
            if success:
                success_count += 1
                logger.info(f"✓ Case {idx} processed successfully")
            else:
                error_count += 1
                logger.error(f"✗ Case {idx} failed: {error}")
                
        except Exception as e:
            error_count += 1
            logger.error(f"✗ Case {idx} error: {e}", exc_info=True)
    
    logger.info(f"\n=== Processing Complete ===")
    logger.info(f"Success: {success_count}/19")
    logger.info(f"Errors: {error_count}/19")

# Case 1
add_case("""Aldana Ramos v. Holder, Jr.
Court of Appeals for the First Circuit

Citations: 757 F.3d 9, 2014 WL 2915920
Docket Number: 13-2022
Judges: Lynch, Torruella, Thompson
Other Dates: June 27, 2014.
Opinion
Authorities (25)
Cited By (58)
Summaries (14)
Similar Cases (7.1K)
PDF
Headmatter
Elvis Leonel ALDANA-RAMOS; Robin Obdulio Aldana-Ramos, Petitioners, v. Eric H. HOLDER, Jr., Attorney General of the United States, Respondent.

No. 13-2022.

United States Court of Appeals, First Circuit.

June 27, 2014.
Amended Aug. 8, 2014.

*11 William P. Joyce and Joyce & Associates P.C. on brief for petitioners.

*12 Stuart F. Delery, Assistant Attorney General, Civil Division, Song Park, Senior Litigation Counsel, and Sunah Lee, Trial Attorney, Office of Immigration Litigation, on brief for respondent.

Before LYNCH, Chief Judge, TORRUELLA and THOMPSON, Circuit Judges.
Combined Opinion by Lynch
LYNCH, Chief Judge.
Petitioners Elvis Leonel Aldana Ramos ("Elvis") and Robin Obdulio Aldana Ramos ("Robin") seek review of an order of the Board of Immigration Appeals ("BIA") denying their applications for asylum, withholding of removal, and protection under the Convention Against Torture ("CAT"). The BIA concluded that the petitioners had not made the requisite showings that they were or will be persecuted on account of membership in a protected social group or that it is more likely than not that they would be tortured by government authorities upon returning to their home country. Because the BIA's conclusion as to the asylum claim is legally flawed and is not supported by the record as currently developed, we grant the petition in part and remand to the BIA for further proceedings as to the asylum and withholding of removal claims. We deny the petition as to the CAT claim.

I.

We recount the facts as presented by the record, noting that the Immigration Judge ("U") found that petitioners were credible. Elvis and Robin are brothers and are natives and citizens of Guatemala. At the time of the relevant events, Elvis was 20 years old and Robin was 18. Their father, Haroldo Aldana-Córdova ("Harol-do"), owned a successful used car business and a real estate rental business in Sala-má, Guatemala. Elvis and Robin worked with their father in the family business. The family was relatively well-off and was able to travel to the United States on vacation.

On February 4, 2009, Haroldo asked Elvis and Robin to attend to certain ongoing used car and property rental business concerns while he showed a rental apartment to potential tenants in another town. Both Elvis and Robin were to meet with a buyer interested in purchasing a truck, and Elvis was later supposed to show a rental property to potential tenants. Elvis later called Haroldo to tell him that the buyer was interested in purchasing a truck from the dealership, but there was no answer on Haroldo's phone. Elvis left Robin to conclude the truck sale while he went to show the apartment. Soon after, an unknown person approached Robin at the dealership and told him that Haroldo had been kidnapped for ransom. Robin called Elvis, who immediately went to the police station to report the kidnapping. According to the petitioners, the police took no real action on the kidnapping report. Elvis and Robin later learned that the kidnappers belonged to a group known as the "Z" gang, a well known criminal organization in Guatemala with ties to drug trafficking.

On February 5, Haroldo called Elvis and Robin and told them that his kidnappers demanded one million quetzales (approximately $125,000) in ransom by noon of that day and would kill him if they did not pay the entire ransom. The next day, Haroldo called again to repeat the message. Haroldo instructed Elvis and Robin to pawn the car dealership to Marlon Martínez, a family friend and business associate. 1 *13 Martinez already owed Haroldo's family 150,000 quetzales but he did not help them raise the ransom money.

Over the next three days, Elvis and Robin collected 400,000 quetzales and paid it to the kidnappers. The kidnappers continued to refuse to release Haroldo until the ransom was paid in full. Around that same time, men in vehicles without license plates began driving around petitioners' home. The brothers found the action intimidating. According to an affidavit Elvis later submitted, this was a threatening tactic frequently used by the "Z" gang.

Eventually, Elvis and Robin borrowed the remaining 600,000 quetzales, largely from relatives, and paid the sum over to the kidnappers. The brothers state that they completely exhausted their financial resources in doing so. The kidnappers told the brothers where they could retrieve their father. When they arrived at that location, they could not find him. Nor did he turn up. Four days later, the police called Elvis and told him Haroldo had been murdered and his body had been found in a different town.

After Haroldo's murder, several members of the "Z" gang were arrested and charged with the killing. One of those members was Marlon Martinez, Jr., the son of Haroldo's business associate. The brothers eventually learned that the Martinez family was involved in the entire kidnapping and intimidation ordeal. The charges against all of the suspects were eventually dropped; Elvis testified that the reason the charges were dropped was that the judge was paid off.

Although Haroldo was dead and the ransom paid, the threats against petitioners resumed. About a month after Haroldo's funeral, Elvis was followed from the dealership by a car with no license plates, which he recognized as one of the same cars that had earlier circled his house. In fear, Elvis abandoned his car and fled on foot after evading the follower. To keep Robin safe, Elvis sent him to stay with their aunt in a different town, about four hours away from their home. Elvis eventually joined them, after receiving continuing threats from unmarked cars. Elvis had taken to traveling to work at odd hours, using different vehicles with tinted windows. Eventually, unmarked cars began appearing at petitioners' aunt's house. On one occasion, she saw several heavily armed men get out of the cars and circle the house as if they were looking for someone.

By mid-2009, the brothers fled to the United States. Robin entered on a tourist visa on March 3, 2009, and Elvis entered on a tourist visa on July 5, 2009.

On February 5, 2010, petitioners filed their timely application for asylum and withholding of removal. Petitioners argued that they were persecuted on account of their membership in a particular social group, which they defined as their immediate family. The case was referred to the Immigration Court for removal proceedings.

An IJ heard the case in January 2012. The IJ found that petitioners' testimony was credible, noting that it "was internally consistent and consistent as well with the detailed written statement that they each offered in support of their applications." The IJ went on to deny their applications "for failure to make a nexus between the past persecution that they claim on account of [their] membership in their nuclear family and any of the enumerated grounds." The IJ explained that "the social group claimed does not meet the requirements of particular social visibility *14 and ... that, rather, the respondents' family has been a victim of criminal activity in the country of Guatemala." The IJ also denied the application under the CAT, finding that petitioners made "no claim that they would be tortured by the government of Guatemala if returned to that country."

Petitioners appealed to the BIA. The BIA affirmed, adopting the IJ's decision and supplementing it with its own findings. Specifically, the BIA concluded that "[t]he evidence shows that criminals kidnapped the respondents' father to obtain money from him and his family!;] it does not demonstrate that the harm [they] suffered in Guatemala was on account of their race, religion, nationality, membership in a particular social group, or political opinion." It further concluded that "[t]he respondents did not demonstrate that Marlon Martinez ... or Mr. Martinez's son was associated with the 'Z' gang or that they sought to harm the respondents for any reason including on account of a protected ground." 2 The BIA concluded that although Haroldo was certainly the victim of "a terrible crime," the crime was motivated by the "Z" gang's perception of his wealth "and not on account of a protected characteristic of the respondents' father or of their family." Elvis and Robin timely petitioned this court for review.

II.

Where the BIA adopts an IJ's decision and supplements the decision with its own findings, as here, we review the decisions of both the BIA and the IJ. See Romilus v. Ashcroft, 385 F.3d 1, 5 (1st Cir.2004). We must uphold the BIA's decision if it is "supported by reasonable, substantial, and probative evidence on the record considered as a whole." I.N.S. v. Elias-Zacarias, 502 U.S. 478, 481, 112 S.Ct. 812, 117 L.Ed.2d 38 (1992) (quoting 8 U.S.C. § 1105a(a)(4)) (internal quotation marks omitted); accord Sam v. Holder, 752 F.3d 97, 99 (1st Cir.2014). "To reverse the BIA['s] finding we must find that the evidence not only supports [a contrary] conclusion, but compels it...." Elias-Zacarias, 502 U.S. at 481 n. 1, 112 S.Ct. 812. We review the BIA's legal conclusions de novo, although we grant some deference to its interpretations of statutes and regulations related to immigration matters. Matos-Santana v. Holder, 660 F.3d 91, 93 (1st Cir.2011).

To qualify for asylum, petitioners must establish that they are "refugee[s]." 8 U.S.C. § 1158(b)(1)(A); 8 C.F.R. § 1208.13(a). A refugee is "someone who is unable or unwilling to return to his home country due to persecution or a well-founded fear of future persecution 'on account of race, religion, nationality, membership in a particular social group, or political opinion.' " Silva v. Gonzales, 463 F.3d 68, 71 (1st Cir.2006) (quoting 8 U.S.C. § 1101(a)(42)(A)).

The IJ's conclusion turned entirely on whether petitioners had established a sufficient "nexus" between their claimed persecution and the particular social group — that is, whether they were persecuted "on account of' their family mem *15 bership. 3 The BIA's opinion likewise focused on the "on account of' element. Because understanding petitioners' claimed social group and persecution is necessary to determining whether the persecution was "on account of' membership in the social group, we address each of these elements in turn. We do so bearing in mind the Supreme Court's instruction that the "ordinary ... rule" is to remand to the BIA to allow it to make case-specific determinations in the first instance. I.N.S. v. Orlando Ventura, 537 U.S. 12, 18, 123 S.Ct. 353, 154 L.Ed.2d 272 (2002).

A. Particular Social Group

In this case, petitioners argue that they are members of a "particular social group," which they define as their immediate family. It is well established in the law of this circuit that a nuclear family can constitute a particular social group "based on common, identifiable and immutable characteristics." Gebremichael v. I.N.S., 10 F.3d 28, 36 (1st Cir.1993); see Ruiz v. Mukasey, 526 F.3d 31, 38 (1st Cir.2008) ("Kinship can be a sufficiently permanent and distinct characteristic to serve as the linchpin for a protected social group within the purview of the asylum laws."). And we are not aware of any circuit that has reached a contrary conclusion. 4

Athough the record is not entirely clear, the BIA appears to have concluded in this case that a family cannot qualify as a particular social group unless a member of the family (or, perhaps, the family itself) can also claim another protected ground. Specifically, the BIA stated: "[T]he 'Z' gang was motivated by criminal intent to misappropriate money from the respondents' father and not on account of a protected characteristic of the respondents' father or of their family." (emphasis added). 5 The law in this circuit and others is clear that a family may be a particular social group simply by virtue of its kinship ties, without requiring anything more. See Gebremichael, 10 F.3d at 35-36 & n. 20 (explaining that a family may be a particular social group and that, although social group membership often overlaps with other protected grounds, "social group persecution can be an independent basis of refugee status"); see also Ruiz, 526 F.3d at 38 (explaining that asylum claim can succeed where "family membership itself brings about the perseeutorial conduct"); Thomas v. Gonzales, 409 F.3d 1177, 1188-89 (9th Cir.2005) (en banc) ("[T]here is nothing in the statute ... to *16 suggest that membership in a family is insufficient, standing alone, to constitute a particular social group in the context of establishing eligibility for asylum or withholding of removal."), vacated on other grounds, 547 U.S. 183, 126 S.Ct. 1613, 164 L.Ed.2d 358 (2006); Iliev v. I.N.S., 127 F.3d 638, 642 (7th Cir.1997) (requiring petitioner to "demonstrate that his family was a particular target for persecution" without requiring showing of additional protected ground).

Our interpretation is consistent with the language of the statute. The BIA has used the principle in its interpretation of the statute that there is no indication that Congress intended the phrase "membership in a particular social group" to have any particular meaning, and Congress borrowed the term directly from the United Nations Protocol Relating to the Status of Refugees, Jan. 31, 1967, 19 U.S.T. 6223. See In re Acosta, 19 I. & N. Dec. 211, 232 (B.I.A.1985). Ultimately using the doctrine of ejusdem generis, the BIA has noted that a "purely linguistic analysis of this ground" shows that it can encompass "persecution seeking to punish either people in a certain relation, or having a certain degree of similarity, to one another or people of like class or kindred interests," including based on "family background." Id. at 232-33 (citing G. Goodwin-Gill, The Refugee in International Law 31 (1983)). And although this ground "may frequently overlap with persecution on other grounds such as race, religion, or nationality," id. at 233, there is no indication in the text that it must overlap. The BIA has interpreted the phrase "persecution on account of membership in a particular social group" to mean "persecution that is directed toward an individual who is a member of a group of persons all of whom share a common, immutable characteristic." Id.

The factual record here does not preclude and would even allow the BIA to find that petitioners are members of a particular social group by virtue of their family relationship, without any need to show a further protected ground. We express no opinion on whether such a finding is compelled by the record or whether petitioners' family in particular meets the criteria for a particular social group, leaving the issue to the BIA in the first instance. See Orlando Ventura, 537 U.S. at 18, 123 S.Ct. 353.

B. Persecution

Next, petitioners argue that they were persecuted in Guatemala. They recount the series of crimes committed against their family: the kidnapping, ransom, and murder of their father; intimidation using unmarked vehicles during the kidnapping period; resumed intimidation in the same manner after their father's death; and the appearance of unmarked cars and heavily armed men at their aunt's house four hours away. Additionally, petitioners point to their own testimony, which the IJ concluded was credible, that they fear they will be killed if they are sent back to Guatemala.

Whether a set of experiences rises to the level of persecution is decided on a case-by-case basis, Raza v. Gonzales, 484 F.3d 125, 129 (1st Cir.2007), although "[t]o rise to the level of persecution, the sum of an alien's experiences must add up to more than ordinary harassment, mistreatment, or suffering," Lopez de Hincapie v. Gonzales, 494 F.3d 213, 217 (1st Cir.2007). "[T]hreats of murder would fit neatly under this carapace." Lopez de Hincapie, 494 F.3d at 217. This case includes far more than mere threats of mur *17 der. 6 And other circuits have held that factual scenarios very similar to this one did rise to the level of persecution. See Tapiero de Orejuela v. Gonzales, 423 F.3d 666, 672-73 (7th Cir.2005) (finding persecution against wealthy family where paramilitary group followed them, murdered father, demanded money, and threatened remaining family members).

The government attempts a re-characterization of the facts. It argues that "there were no 'threats' [against petitioners after their father's death] because the people [in the unmarked cars] never approached or spoke to Elvis or anyone at his aunt's house." We disagree. No reasonable factfinder could so interpret the facts here. Petitioners testified credibly that the unmarked ears were subjectively intimidating, that they were a common intimidation tool used by the "Z" gang, and, according to Elvis's affidavit, that heavily armed men got out of the vehicles at their aunt's house and walked around the property, when that had never happened before. If the government intends a rule that there is no persecution or even threats where threats are not verbalized, it is wrong as a matter of law. Cf. Un v. Gonzales, 415 F.3d 205, 209-10 (1st Cir. 2005) (recognizing the possibility of "implicit" death threats and that those threats, taken in context with other hostile actions including more explicit threats, could support a finding of persecution). The fact that no words were exchanged does not mean those actions were not threatening.

"Persecution also 'always implies some connection to government action or inaction,' whether in the form of direct government action, 'government-supported action, or government's unwillingness or inability to control private conduct.' " Ivanov v. Holder, 736 F.3d 5, 12 (1st Cir.2013) (quoting Sok v. Mukasey, 526 F.3d 48, 54 (1st Cir.2008)). Here, petitioners offered evidence of such a connection: they testified to their belief that the murder charges were dismissed because the local judge was paid off. They also testified that the police were unwilling or unable to investigate the "Z" gang's activities, particularly the kidnapping. And they were found credible.

The BIA never addressed whether this testimony established the necessary connection between petitioners' experiences and the Guatemalan government's unwillingness or inability to control private conduct. We leave the question to the BIA on remand but observe that this testimony would at least allow such a finding.

For these reasons, we conclude that the record does not preclude but permits the BIA to find that persecution occurred here. We again express no opinion as to whether such a finding is compelled on this record. See Orlando Ventura, 537 U.S. at 18, 123 S.Ct. 353.

C. "On Account Of"

The final element of the asylum claim, and the most contested in this case, is whether the BIA applied the correct analysis to determine whether petitioners were *18 persecuted "on account of' their membership in their family. Both the BIA and the IJ concluded that petitioners had not drawn a sufficient connection between their membership in their nuclear family and the criminal actions taken against them. The BIA concluded that the "Z" gang "targeted [Haroldo] because they believed he was a wealthy person, ... and not on account of a protected characteristic of the respondents' father or of their family." This conclusion, of course, is directed toward Haroldo and not toward petitioners.

Petitioners argue that this focus on Har-oldo fails to account for their own claims. They make two further arguments that the BIA's conclusion entirely misses the focus of what the family as-a particular social group means. First, and most importantly, they argue that the BIA's conclusion that petitioners were targeted on the basis of wealth is unsupported by the record. Petitioners point to their credible testimony that they exhausted all of their own and their family's financial resources in trying to raise the money to ransom their father, and yet were still followed by members of the "Z" gang in unmarked cars even after their father's funeral. That testimony creates an inference that the "Z" gang targeted petitioners because of their membership in a particular (and perhaps somewhat prominent) family.

Neither the BIA nor the IJ ever addressed this argument. That is insufficient. 7

Independently, petitioners also correctly point out that asylum is still proper in mixed-motive cases even where one motive would not be the basis for asylum, so long as one of the statutory protected grounds is "at least one central reason" for the persecution. 8 U.S.C. § 1158(b)(1)(B)(i). In other words, even though criminal targeting based on wealth does not qualify as persecution "on account of' membership in a particular group, see Sicaju-Diaz v. Holder, 663 F.3d 1, 3-4 (1st Cir.2011), the statute still allows petitioners to claim asylum if petitioners' family relationship was also a central reason for the persecution against them.

The BIA, however, concluded that because the initial crimes were at least partly motivated by wealth, none of the persecution against petitioners could have been based on a protected ground. Specifically, the BIA explained:

The respondent's [sic] father was a victim of a terrible crime in Guatemala by the "Z" gang who targeted him because they believed he was a wealthy person. Thus, the "Z" gang was motivated by criminal intent to misappropriate money from the respondents' father and not on account of a protected characteristic of respondents' father or of their family.
It is unclear whether the BIA intended a general rule to this effect or meant that on these facts, the existence of a wealth motive forecloses the possibility of a protected ground. In either case, we are aware of no legal authority supporting the proposition that, if wealth is one reason for the alleged persecution of a family member, a protected ground — such as family membership — cannot be as well. To the contrary, the plain text of the statute, which allows an applicant to establish refugee status if the protected ground is "at least one central reason" for the persecution, clearly contemplates the possibility that *19 multiple motivations can exist, and that the presence of a non-protected motivation does not render an applicant ineligible for refugee status. See 8 U.S.C. § 1168(b)(1)(B)(i).
To be sure, if wealth is the sole reason for targeting a group of people, the fact that the group is a family unit does not convert the non-protected criminal motivation into persecution on the basis of family connections. See Perlera-Sola v. Holder, 699 F.3d 572, 577 (1st Cir.2012). 8 Each case depends on the facts. There may be scenarios in which a wealthy family, targeted in part for its wealth, may still be the victims of persecution as a family. For instance, a local militia could single out a prominent wealthy family, kidnap family members for ransom, effectively drive the family into poverty, and pursue them throughout the country in order to show the local community that even its most prominent families are not immune and that the militia's rule must be respected. That is one of a number of examples.

In this case, we leave to the BIA the question of whether the family relationship was, in addition to wealth, a central factor behind the persecution. At this stage in the proceedings, we simply observe that the record is more than sufficient to allow such a finding.

III.

The BIA also rejected petitioners' claim for CAT protection. A petitioner seeking CAT protection must show "it is more likely than not" that he would be subject to torture "by or with the aequies-cence of a government official." Nako v. Holder, 611 F.3d 45, 50 (1st Cir.2010). As the BIA noted, there is no evidence of government acquiescence here. According to petitioners' testimony, and in contrast to their description of police inaction following the kidnapping, the police did investigate their father's murder and made arrests in the case. The only evidence that could arguably be construed to show government acquiescence in the "Z" gang's activities was Elvis's testimony that the judge who released the suspects had been paid off, but petitioners have made no showing that similar bribery would likely occur in a future case. Without a showing of government participation or acquiescence, petitioners' claim for CAT protection fails.

IV.

The BIA's decision as to petitioners' asylum claim was not supported by substantial evidence because it neglected the evidence in support of petitioners' claim and was based on a legal error because it did not allow for the possibility of mixed motives. The decision as to the CAT claim, on the other hand, was supported by substantial evidence. Consequently, the petition for review is granted in part and denied in part. We vacate the BIA's decision as to the asylum and withholding of removal claims and remand for further proceedings consistent with this opinion.

So ordered.""")

# Case 2
add_case("""Immigration & Naturalization Service v. Elias-Zacarias
Supreme Court of the United States

Citations: 502 U.S. 478, 112 S. Ct. 812, 117 L. Ed. 2d 38, 1992 U.S. LEXIS 550
Docket Number: 90-1342
Judges: Scalia, Rehnquist, White, Kennedy, Souter, Thomas, Stevens, Blackmun, O'Connor
Other Dates: Argued November 4, 1991
Opinion
Authorities (12)
Cited By (7.2K)
Summaries (765)
Similar Cases (5.8K)
PDF
Headmatter
IMMIGRATION AND NATURALIZATION SERVICE v. ELIAS-ZACARIAS

No. 90-1342.
Argued November 4, 1991
Decided January 22, 1992

Scalia, J., delivered the opinion of the Court, in which Rehnquist, C. J., and White, Kennedy, Souter, and Thomas, JJ., joined. Stevens, J., filed a dissenting opinion, in which Blackmun and O'Connor, JJ., joined, post, p. 484.
Maureen E. Mahoney argued the cause for petitioner. On the briefs were Solicitor General Starr, Assistant Attorney General Gerson, Acting Deputy Solicitor General Wright, Stephen J. Marzen, and Alice M. King.

*479 James Robertson argued the cause for respondent. With him on the brief were Carol F. Lee and Peter A. Von Mehren. *
 * Briefs of amici curiae urging affirmance were filed for the American Immigration Lawyers Association by Kevin R. Johnson, Joshua R. Flown, and Robert Rubin; for the Lawyers Committee for Human Rights et al. by Arthur C. Helton, 0. Thomas Johnson, Jr., and Andrew I. Schoen-koltz; and for the United Nations High Commissioner for Refugees by Arthur L. Bentley III and Julian Fleet ↵
Lead Opinion by Scalia
Justice Scalia delivered the opinion of the Court.
The principal question presented by this case is whether a guerrilla organization's attempt to coerce a person into performing military service necessarily constitutes "persecution on account of . . . political opinion" under § 101(a)(42) of the Immigration and Nationality Act, as added, 94 Stat. 102, 8 U. S. C. § 1101(a)(42).

I

Respondent Elias-Zacarias, a native of Guatemala, was apprehended in July 1987 for entering the United States without inspection. In deportation proceedings brought by petitioner Immigration and Naturalization Service (INS), Elias-Zacarias conceded his deportability but requested asylum and withholding of deportation.

The Immigration Judge summarized Elias-Zacarias' testimony as follows:

"[A]round the end of January in 1987 [when Elias-Zacarias was 18], two armed, uniformed guerrillas with handkerchiefs covering part of their faces came to his home. Only he and his parents were there. . . . [T]he guerrillas asked his parents and himself to join with them, but they all refused. The guerrillas asked them why and told them that they would be back, and that they should think it over about joining them.
*480"[Elias-Zacarias] did not want to join the guerrillas because the guerrillas are against the government and he was afraid that the government would retaliate against him and his family if he did join the guerrillas. [H]e left Guatemala at the end of March [1987] . . . because he was afraid that the guerrillas would return." App. to Pet. for Cert. 40a-41a.
The Immigration Judge understood from this testimony that Elias-Zacarias' request for asylum and for withholding of deportation was "based on this one attempted recruitment by the guerrillas." Id., at 41a. She concluded that Elias-Zacarias had failed to demonstrate persecution or a well-founded fear of persecution on account of race, religion, nationality, membership in a particular social group, or political opinion, and was not eligible for asylum. See 8 U. S. C. §§ 1101(a)(42), 1158(a). She further concluded that he did not qualify for withholding of deportation.

The Board of Immigration Appeals (BIA) summarily dismissed Elias-Zacarias' appeal on procedural grounds. Elias-Zacarias then moved the BIA to reopen his deportation hearing so that he could submit new evidence that, following his departure from Guatemala, the guerrillas had twice returned to his family's home in continued efforts to recruit him. The BIA denied reopening on the ground that even with this new evidence Elias-Zacarias had failed to make a prima facie showing of eligibility for asylum and had failed to show that the results of his deportation hearing would be changed.

The Court of Appeals for the Ninth Circuit, treating the BIA's denial of the motion to reopen as an affirmance on the merits of the Immigration Judge's ruling, reversed. 921 F. 2d 844 (1990). The court ruled that acts of conscription by a nongovernmental group constitute persecution on account of political opinion, and determined that Elias-Zacarias had a "well-founded fear" of such conscription. Id., at 850-852. We granted certiorari. 500 U. S. 915 (1991).

*481II Section 208(a) of the Immigration and Nationality Act, 8 U. S. C. § 1158(a), authorizes the Attorney General, in his discretion, to grant asylum to an alien who is a "refugee" as defined in the Act, i. e., an alien who is unable or unwilling to return to his home country "because of persecution or a well-founded fear of persecution on account of race, religion, nationality, membership in a particular social group, or political opinion." § 101(a)(42)(A), 8 U. S. C. § 1101(a)(42)(A). See INS v. Cardoza-Fonseca, 480 U. S. 421, 423, 428, n. 5 (1987). The BIA's determination that Elias-Zacarias was not eligible for asylum must be upheld if "supported by reasonable, substantial, and probative evidence on the record considered as a whole." 8 U. S. C. § 1105a(a)(4). It can be reversed only if the evidence presented by Elias-Zacarias was such that a reasonable factfinder would have to conclude that the requisite fear of persecution existed. NLRB v. Columbian Enameling & Stamping Co., 306 U. S. 292, 300 (1939).1 The Court of Appeals found reversal warranted. In its view, a guerrilla organization's attempt to conscript a person into its military forces necessarily constitutes "persecution on account of. . . political opinion," because "the person resisting forced recruitment is expressing a political opinion hostile to the persecutor and because the persecutors' motive in carrying out the kidnapping is political." 921 F. 2d, at 850. The first half of this seems to us untrue, and the second half irrelevant.
*482Even a person who supports a guerrilla movement might resist recruitment for a variety of reasons — fear of combat, a desire to remain with one's family and friends, a desire to earn a better living in civilian life, to mention only a few. The record in the present case not only failed to show a political motive on Elias-Zacarias' part; it showed the opposite. He testified that he refused to join the guerrillas because he was afraid that the government would retaliate against him and his family if he did so. Nor is there any indication (assuming, arguendo, it would suffice) that the guerrillas erroneously believed that Elias-Zacarias' refusal was politically based.

As for the Court of Appeals' conclusion that the guerrillas' "motive in carrying out the kidnapping is political": It apparently meant by this that the guerrillas seek to fill their ranks in order to carry on their war against the government and pursue their political goals. See 921 F. 2d, at 850 (citing Arteaga v. INS, 836 F. 2d 1227, 1232, n. 8 (CA9 1988)); 921 F. 2d, at 852. But that does not render the forced recruitment "persecution on account of . . . political opinion." In construing statutes, "we must, of course, start with the assumption that the legislative purpose is expressed by the ordinary meaning of the words used." Richards v. United States, 369 U. S. 1, 9 (1962); see Cardoza-Fonseca, supra, at 431; INS v. Phinpathya, 464 U. S. 183, 189 (1984). The ordinary meaning of the phrase "persecution on account of . . . political opinion" in § 101(a)(42) is persecution on account of the victim's political opinion, not the persecutor's. If a Nazi regime persecutes Jews, it is not, within the ordinary meaning of language, engaging in persecution on account of political opinion; and if a fundamentalist Moslem regime persecutes democrats, it is not engaging in persecution on account of religion. Thus, the mere existence of a generalized "political" motive underlying the guerrillas' forced recruitment is inadequate to establish (and, indeed, goes far to refute) the proposition that Elias-Zacarias fears persecution on account of political opinion, as §101(a)(42) requires.

*483Elias-Zacarias appears to argue that not taking sides with any political faction is itself the affirmative expression of a political opinion. That seems to us not ordinarily so, since we do not agree with the dissent that only a "narrow, grudging construction of the concept of 'political opinion,' " post, at 487, would distinguish it from such quite different concepts as indifference, indecisiveness, and risk averseness. But we need not decide whether the evidence compels the conclusion that Elias-Zacarias held a political opinion. Even if it does, Elias-Zacarias still has to establish that the record also compels the conclusion that he has a "well-founded fear" that the guerrillas will persecute him because of that political opinion, rather than because of his refusal to fight with them. He has not done so with the degree of clarity necessary to permit reversal of a BIA finding to the contrary; indeed, he has not done so at all.2

Elias-Zacarias objects that he cannot be expected to provide direct proof of his persecutors' motives. We do not require that. But since the statute makes motive critical, he must provide some evidence of it, direct or circumstantial. And if he seeks to obtain judicial reversal of the BIA's determination, he must show that the evidence he presented was *484so compelling that no reasonable factfinder could fail to find the requisite fear of persecution. That he has not done.

The BIA's determination should therefore have been upheld in all respects, and we reverse the Court of Appeals' judgment to the contrary.

It is so ordered.

 Quite beside the point, therefore, is the dissent's assertion that "the record in this case is more than adequate to support the cone lusion that this respondent's refusal [to join the guerrillas] was a form of expressive conduct that constituted the statement of a `political opinion," post, at 488 (emphasis added). To reverse the BIA finding we must find that the evidence not only supports that conclusion, but compels it-and also compels the further conclusion that Elias-Zacarias had a well-founded fear that the guerrillas would persecute him because of that political opinion. ↵
 The dissent misdescribes the record on this point in several respects. For example, it exaggerates the "well foundedness" of whatever fear Elias-Zacarias possesses, by progressively transforming his testimony that he was afraid the guerrillas would " 'take me or kill me,' " post, at 484, into, first, "the guerrillas' implied threat to 'take' him or to 'kill' him," post, at 489 (emphasis added), and, then, into the flat assertion that the guerrillas "responded by threatening to 'take' or to 'kill' him," post, at 490 (emphasis added). The dissent also erroneously describes it as "undisputed" that the cause of the harm Elias-Zacarias fears, if that harm should occur, will be "the guerrilla organization's displeasure with his refusal to join them in their armed insurrection against the government." Post, at 484 (emphasis added). The record shows no such concession by the INS, and all Elias-Zacarias said on the point was that he feared being taken or killed by the guerrillas. It is quite plausible, indeed likely, that the taking would be engaged in by the guerrillas in order to augment their troops rather than show their displeasure; and the killing he feared might well be a killing in the course of resisting being taken. ↵
Dissent by Stevens
Justice Stevens, with whom Justice Blackmun and Justice O'Connor join, dissenting.
Respondent refused to join a guerrilla organization that engaged in forced recruitment in Guatemala. He fled the country because he was afraid the guerrillas would return and "take me and kill me." 1 After his departure, armed guerrillas visited his family on two occasions searching for him. In testimony that the hearing officer credited, he stated that he is still afraid to return to Guatemala because "these people" can come back to "take me or kill me." 2

It is undisputed that respondent has a well-founded fear that he will be harmed, if not killed, if he returns to Guatemala. It is also undisputed that the cause of that harm, if it should occur, is the guerrilla organization's displeasure with his refusal to join them in their armed insurrection against the government. The question of law that the case presents is whether respondent's well-founded fear is a "fear of persecution on account of. . . political opinion" within the meaning of § 101(a)(42) of the Immigration and Nationality Act.3

*485If respondent were to prevail, as he did in the Court of Appeals, 921 F. 2d 844 (CA9 1990), he would be classified as a "refugee" and therefore be eligible for a grant of asylum. He would not be automatically entitled to that relief, however, because "the Attorney General is not required to grant asylum to everyone who meets the definition of refugee." INS v. Cardoza-Fonseca, 480 U. S. 421, 428, n. 5 (1987) (emphasis in original). Instead, § 208 of the Act provides that the Attorney General may, "in [his] discretion," grant asylum to refugees.4

*486Today the Court holds that respondent's fear of persecution is not "on account of . . . political opinion" for two reasons. First, he failed to prove that his refusal to join the guerrillas was politically motivated; indeed, he testified that he was at least in part motivated by a fear that government forces would retaliate against him or his family if he joined the guerrillas. See ante, at 482-483. Second, he failed to prove that his persecutors' motives were political. In particular, the Court holds that the persecutors' implicit threat to retaliate against respondent "because of his refusal to fight with them," ante, at 483, is not persecution on account of political opinion. I disagree with both parts of the Court's reasoning.

I

A political opinion can be expressed negatively as well as affirmatively. A refusal to support a cause — by staying home on election day, by refusing to take an oath of allegiance, or by refusing to step forward at an induction center — can express a political opinion as effectively as an affirmative statement or affirmative conduct. Even if the refusal is motivated by nothing more than a simple desire to continue living an ordinary life with one's family, it is the kind of political expression that the asylum provisions of the statute were intended to protect.

As the Court of Appeals explained in Bolanos-Hernandez v. INS, 767 F. 2d 1277 (CA9 1985):

"Choosing to remain neutral is no less a political decision than is choosing to affiliate with a particular political faction. Just as a nation's decision to remain neutral is a political one, see, e. g., Neutrality Act of 1939, 22 U. S. C. §§441-465 (1982), so is an individual's. When a person is aware of contending political forces and af*487firmatively chooses not to join any faction, that choice is a political one. A rule that one must identify with one of two dominant warring political factions in order to possess a political opinion, when many persons may, in fact, be opposed to the views and policies of both, would frustrate one of the basic objectives of the Refugee Act of 1980 — to provide protection to all victims of persecution regardless of ideology. Moreover, construing 'political opinion' in so short-sighted and grudging a manner could result in limiting the benefits under the ameliorative provisions of our immigration laws to those who join one political extreme or another; moderates who choose to sit out a battle would not qualify." Id., at 1286 (emphasis in original; footnote omitted).
The narrow, grudging construction of the concept of "political opinion" that the Court adopts today is inconsistent with the basic approach to this statute that the Court endorsed in INS v. Cardoza-Fonseca, supra. In that case, relying heavily on the fact that an alien's status as a "refugee" merely makes him eligible for a discretionary grant of asylum — as contrasted with the entitlement to a withholding of deportation authorized by § 243(h) of the Act — the Court held that the alien's burden of proving a well-founded fear of persecution did not require proof that persecution was more likely than not to occur. We explained:

"Our analysis of the plain language of the Act, its symmetry with the United Nations Protocol, and its legislative history, lead inexorably to the conclusion that to show a 'well-founded fear of persecution,' an alien need not prove that it is more likely than not that he or she will be persecuted in his or her home country. We find these ordinary canons of statutory construction compelling, even without regard to the longstanding principle of construing any lingering ambiguities in deportation statutes in favor of the alien. See INS v. Errico, 386 *488U. S. 214, 225 (1966); Costello v. INS, 376 U. S. 120, 128 (1964); Fong Haw Tan v. Phelan, 333 U. S. 6, 10 (1948).
"Deportation is always a harsh measure; it is all the more replete with danger when the alien makes a claim that he or she will be subject to death or persecution if forced to return to his or her home country. In enacting the Refugee Act of 1980 Congress sought to 'give the United States sufficient flexibility to respond to situations involving political or religious dissidents and detainees throughout the world.' H. R. Rep. [96-608, p. 9 (1979)]. Our holding today increases that flexibility by rejecting the Government's contention that the Attorney General may not even consider granting asylum to one who fails to satisfy the strict § 243(h) standard. Whether or not a 'refugee' is eventually granted asylum is a matter which Congress has left for the Attorney General to decide. But it is clear that Congress did not intend to restrict eligibility for that relief to those who could prove that it is more likely than not that they will be persecuted if deported." 480 U. S., at 449-450.
Similar reasoning should resolve any doubts concerning the political character of an alien's refusal to take arms against a legitimate government in favor of the alien. In my opinion, the record in this case is more than adequate to support the conclusion that this respondent's refusal was a form of expressive conduct that constituted the statement of a "political opinion" within the meaning of § 208(a).5

*489II It follows as night follows day that the guerrillas' implied threat to "take" him or to "kill" him if he did not change his position constituted threatened persecution "on account of" that political opinion. As the Court of Appeals explained in Bo lanos-Hernandez:
"It does not matter to the persecutors what the individual's motivation is. The guerrillas in El Salvador do not inquire into the reasoning process of those who insist on remaining neutral and refuse to join their cause. They are concerned only with an act that constitutes an overt manifestation of a political opinion. Persecution because of that overt manifestation is persecution because of a political opinion." 767 F. 2d, at 1287.6
It is important to emphasize that the statute does not require that an applicant for asylum prove exactly why his persecutors would act against him; it only requires him to show that he has a "well-founded fear of persecution on account of political opinion." As we recognized in INS v. Cardoza-Fonseca, the applicant meets this burden if he shows that there is a "reasonable possibility" that he will be perse-*490cubed on account of his political opinion. 480 U. S., at 440 (quoting INS v. Stevic, 467 U. S. 407, 425 (1984)). Because respondent expressed a political opinion by refusing to join the guerrillas, and they responded by threatening to "take" or to "kill" him if he did not change his mind, his fear that the guerrillas will persecute him on account of his political opinion is well founded.7
Accordingly, I would affirm the judgment of the Court of Appeals.""")

# Case 3
add_case("""Mazariegos-Paiz v. Holder
Court of Appeals for the First Circuit

Citations: 734 F.3d 57, 2013 WL 5763263, 2013 U.S. App. LEXIS 21809
Docket Number: 19-1609
Judges: Torruella, Selya, Howard
Opinion
Authorities (32)
Cited By (44)
Summaries (9)
Similar Cases (20.4K)
PDF
Headmatter
Henry MAZARIEGOS-PAIZ, Petitioner, v. Eric H. HOLDER, Jr., Attorney General, Respondent.

No. 12-1382.

United States Court of Appeals, First Circuit.

Oct. 25, 2013.

*60 Randy Olen, on brief, for petitioner.

Stuart F. Delery, Principal Deputy Assistant Attorney General, Civil Division, Anthony C. Payne, Senior Litigation Counsel, Office of Immigration Litigation, and Ali Manuchehry, Trial Attorney, Office of Immigration Litigation, Civil Division, U.S. Department of Justice, on brief, for respondent.

Before TORRUELLA, SELYA and HOWARD, Circuit Judges.
Combined Opinion by Selya
SELYA, Circuit Judge.
Our consideration of the petition for judicial review in this immigration case starts with a jurisdictional puzzle. After piecing together this puzzle, we hold, as a matter of first impression in this circuit, that the administrative exhaustion requirement is satisfied as to particular issues when the agency, either on its own initiative or at the behest of some other party to the proceedings, has addressed those claims on the merits, regardless of whether the petitioner himself raised them. 1 This holding establishes our authority to review the issues advanced in the present petition. Concluding, as we do, that those issues lack bite, we deny the petition.

I. BACKGROUND

The historical facts are straightforward. The petitioner, Henry Mazariegos-Paiz, a Guatemalan national, entered the United States without inspection on August 20, 2006. He reunited there with his cousin, Deny Adolfo Mazariegos-Mazariegos, who had entered illegally at an earlier date.

On February 11, 2008, the Department of Homeland Security (DHS) commenced removal proceedings against the petition *61 er. See 8 U.S.C. § 1182(a)(6)(A)®. He conceded removability, but applied for asylum, withholding of removal, and protection under the United Nations Convention Against Torture (CAT). In support, he claimed both past persecution and a well-founded fear of future persecution based on both his political opinion and his membership in a particular social group. 2 He also claimed a likelihood that he would face torture if he returned to Guatemala.

The DHS also initiated removal proceedings against his cousin Deny, who likewise conceded removability and cross-applied for similar relief. The two sets of proceedings were consolidated.

Before the consolidated proceedings got underway, the Immigration Judge (IJ) noted, without objection, that the only files on record were each man's application for asylum and withholding of removal (Form 1-589). Deny took the lead before the agency and testified that he and the petitioner left Guatemala because they had become targets of persecution. Specifically, he asserted that in August of 2005— roughly one year after their political party, the Great National Alliance (GANA), won the general election — a group of men, ostensibly from the rival Guatemalan Republican Front (FRG), beat the cousins, threatened their lives, and warned that their family would be wiped out unless they "withdrew from politics."

On cross-examination, Deny was asked why his application for withholding of removal was unsupported by affidavits or other corroborating evidence. His counsel interjected that she had prepared affidavits for her clients and had assumed that they were on file with the Immigration Court. She then produced three untranslated Spanish-language documents. Two of these — a police report and a medical report — pertained to an attack against the petitioner's uncle. The third document was a copy of Deny's report to a Guatemalan human rights counselor about the August 2005 incident.

Deny's attorney then requested a continuance in order to submit the missing affidavits, translate the proffered documents, and supply other corroborating evidence. Observing that the case had been pending for over a year, the DHS opposed this request. The IJ denied the continuance and marked the untranslated documents for identification only.

When it came time for the petitioner to testify, his counsel offered to waive direct examination. She told the IJ that the petitioner's testimony was "expected to corroborate that of [his cousin] so it would be mostly repetitive." The IJ accepted this representation, and the DHS proceeded to cross-examine the petitioner.

At the conclusion of the hearing, the IJ denied the cousins' applications for withholding of removal and protection under the CAT. She grounded this decision principally on a determination that neither man had testified credibly. In this regard, she noted numerous discrepancies between the applications for relief and the testimony offered at the hearing. She found that the story that the two cousins told was vague, implausible, and wholly uncorroborated.

Both the petitioner and his cousin appealed to the Board of Immigration Appeals (BIA). In his brief, the petitioner focused solely on the IJ's (allegedly erroneous) decision to consolidate the two cases. In contrast, Deny's brief chal *62 lenged both the adverse credibility determination and the refusal to continue the hearing.

The BIA consolidated the two appeals, adopted and affirmed the IJ's adverse credibility determination, and upheld the other disputed rulings. The BIA made no distinction as to who had raised which claims but, rather, proceeded as if each man had advanced every claim. Based on the foregoing, the BIA affirmed the orders of removal.

The petitioner secured new counsel and filed this timely petition for judicial review. For aught that appears, his cousin has not sought judicial review.

II. ANALYSIS

We divide our analysis into three segments. First, we ponder the existence of subject-matter jurisdiction. Thereafter, we mull two separate merits-related rulings.

A. Jurisdiction.

The government argues that this court lacks subject-matter jurisdiction over the petitioner's claims because he failed to exhaust his administrative remedies with respect to those claims. In elaboration, it points out that even though the petitioner in this venue tries to advance two merits-related claims&emdash;one dealing with the adverse credibility determination and one dealing with the denial of a continuance&emdash; he, himself, did not raise either claim before the BIA. The petitioner's best chance to parry this thrust boils down to the following sequence of events: his case and his cousin's were consolidated; his cousin squarely raised before the BIA the issues that the petitioner now seeks to argue; and the BIA actually adjudicated those issues. So viewed, this sequence sufficiently exhausted the issues.

We begin our inquiry into the existence of subject-matter jurisdiction with first principles. As a court of limited jurisdiction, our authority to act in any given case depends upon the extent to which Congress has imbued us with jurisdiction. See Am. Fiber & Finishing, Inc. v. Tyco Healthcare Grp., LP, 362 F.3d 136, 138 (1st Cir.2004). Pertinently for present purposes, Congress has granted us jurisdiction to review non-constitutional claims arising in the removal context only if "the alien has exhausted all administrative remedies available to the alien as of right." 8 U.S.C. § 1252(d)(1). This exhaustion requirement is jurisdictional; that is, it constitutes a limitation on our power of review. See Athehortua-Vanegas v. INS, 876 F.2d 238, 240 (1st Cir.1989).

We have interpreted this exhaustion requirement as demanding that issues be exhausted in agency proceedings. See, e.g., Makhoul v. Ashcroft, 387 F.3d 75, 80 (1st Cir.2004); Ravindran v. INS, 976 F.2d 754, 761 (1st Cir.1992). Ordinarily, then, an alien who neglects to present an issue to the BIA fails to exhaust his administrative remedies with respect to that issue and, thus, places it beyond our jurisdictional reach.

This method of exhaustion, however, is not exclusive. We think that, short of an alien's direct presentation of an issue to the agency, there is at least one other way in which exhaustion may occur. We explain briefly.

The primary rationale behind the exhaustion requirement is apparent. At bottom, the role of a court on a petition for judicial review of agency action is to appraise the agency's handiwork. Were the court free to delve into the merits of issues not presented to the agency, it would effectively usurp the agency's function. See Unemp't Comp. Comm'n v. Aragon, 329 U.S. 143, 155, 67 S.Ct. 245, 91 L.Ed. 136 *63 (1946). The exhaustion requirement stands as a sentinel against such usurpation. At the same time, it creates a carefully calibrated balance of responsibilities, affording the parties the full benefit of the agency's expertise and allowing the agency the first opportunity to correct its own bevues. See SEC v. Chenery Corp., 332 U.S. 194, 200-01, 209, 67 S.Ct. 1575, 91 L.Ed. 1995 (1947); Sidabutar v. Gonzales, 503 F.3d 1116, 1121 (10th Cir.2007).

In the classic case, this rationale permits a finding of exhaustion when a party has squarely presented an issue to the agency. See, e.g., Sunoto v. Gonzales, 504 F.3d 56, 59 (1st Cir.2007). But it also permits a finding of exhaustion whenever the agency has elected to address in sufficient detail the merits of a particular issue. Cf. INS v. Orlando Ventura, 537 U.S. 12, 16, 123 S.Ct. 353, 154 L.Ed.2d 272 (2002) (emphasizing importance of allowing agency to address questions in first instance). Where an agency has opted to follow the latter course, there is no logical reason why exhaustion should turn on which party (if either) brought the issue to the agency's attention. We hold, therefore, that an issue is exhausted when it has been squarely presented to and squarely addressed by the agency, regardless of which party raised the issue (or, indeed, even if the agency raised it sua sponte).

We do not write on a pristine page. Our holding today is consonant with the holdings of several of our sister circuits. See, e.g., Lopez-Dubon v. Holder, 609 F.3d 642, 644-45 (5th Cir.2010); Lin v. Att'y Gen., 543 F.3d 114, 123-26 (3d Cir.2008); Sidabutar, 503 F.3d at 1121; Abebe v. Gonzales, 432 F.3d 1037, 1041 (9th Cir.2005) (en banc); Hassan v. Gonzales, 403 F.3d 429, 433 (6th Cir.2005); Johnson v. Ashcroft, 378 F.3d 164, 170 (2d Cir.2004). But see Amaya-Artunduaga v. Att'y Gen., 463 F.3d 1247, 1250 (11th Cir.2006) (per cu-riam).
In addition, our holding is structurally sound: by addressing an issue on the merits, 3 an agency is expressing its judgment as to what it considers to be a sufficiently developed issue. When a court defers to that exhaustion-related judgment, it avoids judicial intrusion into the domain that Congress has delegated to the agency. See Orlando Ventura, 537 U.S. at 16, 123 S.Ct. 353. We think it follows that if the BIA deems an issue sufficiently presented to warrant full-dress consideration on the merits, a court should not second-guess that determination but, rather, should agree that such consideration exhausts the issue. See Sidabutar, 503 F.3d at 1119-20.

With this framework in place, we can make short shrift of the government's argument. In this case, the BIA undertook a developed discussion of the merits-related issues that the petitioner now seeks to raise. Consequently, this court has jurisdiction to consider those issues notwithstanding the fact that it was Deny, not the petitioner, who urged them before the BIA.

B. Adverse Credibility Determination.

The IJ rested her decision in this case largely on an adverse credibility determi *64 nation. She found, in essence, that the petitioner and his cousin—who had subscribed to a common story—were not credible. The petitioner challenges that adverse credibility determination.

On a petition for judicial review in an immigration case, our customary focal point is the opinion of the BIA. But when "the BIA adopts portions of the IJ's findings while adding its own gloss, we review both the IJ's and the BIA's decisions as a unit." Chen v. Holder, 703 F.3d 17, 21 (1st Cir.2012). So it is here.

Our review is deferential. We assay findings of fact, including credibility determinations, under the familiar substantial evidence standard. See López-Castro v. Holder, 577 F.3d 49, 52 (1st Cir.2009). This standard requires us to accept the agency's factual findings as long as they are "supported by reasonable, substantial, and probative evidence on the record considered as a whole." INS v. Elias-Zacarias, 502 U.S. 478, 481, 112 S.Ct. 812, 117 L.Ed.2d 38 (1992) (internal quotation marks omitted). This means that the agency's factual findings must endure unless the record is such as to compel a reasonable factfinder to reach a contrary conclusion. See Chhay v. Mukasey, 540 F.3d 1, 5 (1st Cir.2008); Laurent v. Ashcroft, 359 F.3d 59, 64 (1st Cir.2004).

In the case at hand, the supportability of the adverse credibility determination is controlled by the REAL ID Act of 2005. Under that regimen, the IJ is directed to consider all relevant factors, including but not limited to the alien's responsiveness, the consistency (or lack of consistency) between his written and oral statements, and the overall plausibility of his tale. See 8 U.S.C. § 1158(b)(l)(B)(iii). In addition, the IJ is encouraged to weigh the presence or absence of corroborating evidence. See id. § 1158(b)(l)(B)(ii); see also Balachandran v. Holder, 566 F.3d 269, 273 (1st Cir.2009). A reviewing court should assess an IJ's credibility determination through the prism of the statute and in light of the totality of the circumstances. See Rivas-Mira v. Holder, 556 F.3d 1, 4 (1st Cir.2009).

Against this backdrop, we turn to the petitioner's claim for withholding of removal. To be eligible for such relief, an alien "has the burden of proving that, more likely than not, he would be subject to persecution on account of a statutorily protected ground should he be repatriated." Pulisir v. Mukasey, 524 F.3d 302, 308 (1st Cir.2008). The alien can carry this burden by demonstrating either that he has suffered past persecution on account of a statutorily protected ground, "thus creating a rebuttable presumption that he may suffer future persecution" if repatriated, or that "it is more likely than not that he will be persecuted on account of a protected ground upon his return to his native land." Da Silva v. Ashcroft, 394 F.3d 1, 4 (1st Cir.2005).

Here, the petitioner relates his claim of persecution to his political opinion and his membership in a particular social group. These two theories coalesce because the social group to which the petitioner alludes is his political party (the GANA). The only evidence of persecution on account of political animus, however, was out of the mouths of the petitioner and his cousin. 4 The IJ's adverse credibility determination rendered that evidence worthless and led inexorably to the rejection of the claim.

*65 The IJ premised her adverse credibility determination on a series of specific findings. To begin, the IJ questioned Deny's 1-589 application, which chronicled his membership in the FRG. This was a highly relevant fact because Deny and the petitioner asserted that the FRG was the source of the alleged persecution.

Deny offered no convincing explanation for this profession of FRG membership. Although he asserted that his statement was a mistake, this assertion was undercut by evidence that his application had been read to him; that he was fully aware of its contents; and that he had not sought to correct it. Under these circumstances, we believe that the IJ was entitled not only to reject Deny's self-serving explanation but also to doubt his veracity. See Jiang v. Gonzales, 474 F.3d 25, 28 (1st Cir.2007) (explaining that "[wjhere there are two plausible but conflicting views of the evidence, the BIA's choice between them cannot be found to be unsupported by substantial evidence").

The IJ also concluded that the cousins' account of threats to wipe out their family unless they refrained from political activity was implausible. She supported this conclusion by pointing out that neither of the cousins had ever run for, let alone held, political office. Nor was there any extrinsic evidence of political involvement on either man's part. This reasoning is logical, though not inevitable; and there is nothing in the record that would compel a reasonable factfinder to deem the tale of the threat credible.

The IJ also found it troubling that the two cousins failed to produce any corroborating evidence to confirm that they had been beaten by FRG adherents; that they had in fact participated in Guatemalan politics; or that threats had been directed to their family. Where, as here, corroborating evidence appears easily obtainable, the absence of such evidence can be fatal to an alien's application for relief. See Chhay, 540 F.3d at 6. On the facts of this ease, the IJ did not act irrationally in attaching weight to the utter absence of any corroborating evidence. See Muñoz-Monsalve v. Mukasey, 551 F.3d 1, 8 (1st Cir.2008) ("[T]he IJ is warranted in weighing in the balance the existence and availability of corroborating evidence, and the effect of its non-production.").

To sum up, the IJ made a series of specific factual findings that, taken together, cogently support her adverse credibility determination. Accordingly, the adverse credibility determination must be upheld because it is adequately tied to substantial evidence in the record. The denial of the petitioner's application for withholding of removal was, therefore, proper.

This leaves the petitioner's application for protection under the CAT. To gain relief on this application, he had to prove that, more likely than not, he would be tortured if removed to his homeland. See Mariko v. Holder, 632 F.3d 1, 7 (1st Cir.2011); 8 C.F.R. § 1208.16(c)(2). Because the factual underpinnings of this claim are inextricably intertwined with the factual underpinnings of the withholding of removal claim, the IJ's supportable adverse credibility determination dooms both claims. See Mariko, 632 F.3d at 7.

C. Continuance.

The petitioner's last claim of error implicates the denial of his request for a continuance. While an "Immigration Judge may grant a motion for continuance for good cause shown," 8 C.F.R. § 1003.29, the granting of a continuance rests largely in her discretion. See Amouri v. Holder, 572 F.3d 29, 36 (1st Cir.2009); see also *66 Morris v. Slappy, 461 U.S. 1, 11-12, 103 S.Ct. 1610, 75 L.Ed.2d 610 (1983).

We have jurisdiction to review the petitioner's allegation of abuse of discretion with respect to the denial of a continuance, notwithstanding the jurisdictional bar contained in 8 U.S.C. § 1252(a)(2)(B)(ii). See Alsamhouri v. Gonzales, 484 F.3d 117, 121-22 (1st Cir. 2007). We do not find that the agency abused its discretion here.

Under the applicable regulation, 8 C.F.R. § 1003.29, the party who seeks a continuance (here, the petitioner) bears the burden of showing good cause. See Ramchandani v. Gonzales, 434 F.3d 337, 338 (5th Cir.2005). The petitioner offered no convincing reason for his failure, over a period of more than a year, to procure corroborating evidence. By the same token, he offered no convincing explanation for his failure to have the untranslated documents put in proper form. 5 Parties have an obligation, to exercise due diligence in marshaling evidence. Viewed in this light, the IJ's denial of the petitioner's mid-trial request for a continuance was not an abuse of discretion.

In an attempt to fashion a fallback position, the petitioner asserts that the denied continuance deprived him of a fair hearing and, thus, transgressed his right to due process. We have jurisdiction to review this constitutional claim. See 8 U.S.C. § 1252(a)(2)(D). Our review is de novo. See Chhay, 540 F.3d at 8.

Here, the petitioner received all of the process that was due. We already have established that the IJ did not abuse her discretion in denying the request for continuance. See text supra. That being so, there is no basis for a colorable claim that the denied continuance somehow produced a fundamentally unfair hearing. 6 See Alsamhouri, 484 F.3d at 124.

III. CONCLUSION

We need go no further. For the reasons elucidated above, we deny the petition for review.

So Ordered.""")

# Case 4
add_case("""Villalta-Martinez v. Sessions
Court of Appeals for the First Circuit

Citations: 882 F.3d 20
Docket Number: 17-1201P
Judges: Lynch, Stahl, Barron
Opinion
Authorities (21)
Cited By (31)
Summaries (8)
Similar Cases (101)
PDF
Headmatter
Rosa Maria VILLALTA-MARTINEZ, Petitioner,
v.
Jefferson B. SESSIONS, III, Respondent.
No. 17-1201
United States Court of Appeals, First Circuit.
February 7, 2018
Kevin MacMurray and MacMurray & Associates, on brief for petitioner.
Jeffrey R. Meyer, Attorney, Office of Immigration Litigation, Civil Division, United States Department of Justice, Chad A. Readler, Acting Assistant Attorney General, Stephen J. Flynn, Assistant Director, on brief for respondent.
Before Lynch, Stahl, and Barron Circuit Judges.
Lead Opinion by Stahl
STAHL, Circuit Judge.
Petitioner Rosa Maria Villalta-Martinez ("Villalta-Martinez") seeks our review of an order of the Board of Immigration Appeals ("BIA") denying her applications for asylum, withholding of removal, and protection under the Convention Against Torture Act ("CAT"). After careful consideration, we deny the petition for review.

I. Facts & Prior Proceedings

We recite here the relevant factual background. On May 8, 2015, Villalta-Martinez, a citizen of El Salvador, illegally entered the United States. On May 9, 2015, she was apprehended by Border Patrol Agents, charged under 8 U.S.C. § 1182(a)(6)(A)(i), and released on her own recognizance. Villalta-Martinez admitted to her removability, and thereafter, filed *22applications for asylum, withholding of removal, and protection under the CAT, claiming she was persecuted, and faced future persecution, at the hands of Salvadorian gang members, on account of her family membership.1

Villalta-Martinez was the only witness to testify in support of her applications before the Immigration Judge ("IJ"). She provided the following information: From 2012-2015, while in El Salvador, she was in a relationship with Ever Eliseo Garcia-Linares ("Garcia"). She became pregnant with Garcia's child and, although she moved into an apartment with Garcia, the couple never married.

Garcia owned a chain of stores in El Salvador. The Marasalvatrucha gang demanded money from Garcia on a weekly basis. Due to these extortion demands, Garcia left El Salvador with the intent to move to Canada; however, he was apprehended in the United States for illegal reentry, having previously been deported.2

During her relationship with Garcia, Villalta-Martinez worked in one of his stores. She testified that after Garcia left El Salvador, on at least five separate occasions, gang members came to the store that she worked at, put a gun to her head, and demanded money. As a result, Villalta-Martinez moved to another store to work,3 in hopes of avoiding trouble with the gang, but the same thing happened. She testified that the gang members came to that store and demanded $2,000. A gang member told her that if she did not pay, he would pull the unborn child from her womb, cut her, and rape her.

After receiving this threat, Villalta-Martinez obtained $3,000 from an aunt, who also resided in El Salvador, in order to travel to the United States. Villalta-Martinez testified that "she was afraid to return to El Salvador because gang members would take reprisals because she did not comply with their demands for money."

The IJ credited Villalta-Martinez's testimony as true. Nonetheless, the IJ found that Villalta-Martinez: (1) failed to establish that she suffered persecution in El Salvador; and (2) failed to establish that she was persecuted on account of her family membership with Garcia. The IJ explained that "the evidence was not that [Villalta-Martinez] was targeted because of Mr. Garcia, but that she was targeted by gangs and each and every time because they wanted money. The respondent has not established that one of the reasons she was targeted was because of her relationship with Mr. Garcia."

The BIA affirmed the IJ's denial and reasoning. The BIA explained:

[E]ven if [Villalta-Martinez] is considered to be in a familial relationship with a man with whom she was in a romantic relationship and with whom she had a child, the respondent has not established a nexus between her past and future fear of harm by gang members and her familial relationship to the man. The record *23reflects that the respondent was the victim of extortion and that she continues to fear future criminal activity.
Because Villalta-Martinez could not meet her burden for asylum, the BIA determined that "she has also not satisfied the higher standard of a clear probability of persecution" as required for the withholding of removal.

II. Discussion

In order to qualify for asylum, an applicant must demonstrate that she has experienced past persecution or has a well-founded fear of future persecution on account of her "race, religion, nationality, membership in a particular social group, or political opinion." 8 U.S.C. § 1101(a)(42)(A). The standard for withholding of removal is even higher; the applicant must show that it is more likely than not that she would be subject to persecution on account of an enumerated ground if she were repatriated. See id. § 1231(b)(3); Mayorga-Vidal v. Holder, 675 F.3d 9, 13 (1st Cir. 2012).

We first consider whether Villalta-Martinez has established a well-founded fear of persecution based on one of the five statutorily recognized categories. 8 U.S.C. § 1101(a)(42)(A). In her petition for review, Villalta-Martinez's argues that the BIA erred in concluding that there was no evidence establishing a nexus between her past persecution and her proposed social group, her family membership. Villalta-Martinez explains that "[a]lthough money was part of the reasons why gangs targeted her, the main reason was her familial relationship."

Whether an applicant has met his or her burden for proving eligibility is a question of fact, reviewed under the substantial evidence standard. See Hincapie v. Gonzales, 494 F.3d 213, 218 (1st Cir. 2007) ("[W]hether persecution is on account of one of the five statutorily protected grounds is fact-specific"; therefore, "we review the BIA's answer to that question through the prism of the substantial evidence rule."). "We uphold the BIA's findings if they are supported by reasonable, substantial, and probative evidence on the record considered as a whole, and will reverse only if any reasonable adjudicator would be compelled to conclude to the contrary." Ratnasingam v. Holder, 556 F.3d 10, 13 (1st Cir. 2009) (internal quotations and citations omitted). "When the BIA adopts and affirms the IJ's ruling but also examines some of the IJ's conclusions, this Court reviews both the BIA's and IJ's opinions." Perlera-Sola v. Holder, 699 F.3d 572, 576 (1st Cir. 2012).

"[S]howing a linkage to one of the five statutorily protected grounds is 'critical' to a successful asylum claim." Hincapie, 494 F.3d at 218 (quoting I.N.S. v. Elias-Zacarias, 502 U.S. 478, 483, 112 S.Ct. 812, 117 L.Ed.2d 38 (1992) ). In order to sufficiently demonstrate persecution on account of a protected ground, the petitioner "must provide sufficient evidence to forge an actual connection between the harm [suffered] and some statutorily protected ground," beyond a "reasonable possibility of a nexus." Id.

In describing the gang's extortion tactics before the IJ, Villalta-Martinez testified that "[t]here were times that we were able to close the doors on time, but at the end they would be outside waiting for us and they would take us, take all our belongings." On cross-examination, she explained that the gang members would follow her and "the rest of the employee[s]." "They were demanding money from the store and then they demanded directly money from me." When asked if she was targeted for working at the store, she responded "[f]or *24that reason, and also because I was the partner of the owner of the store."

We agree with the finding of the BIA that there is "insufficient evidence in the record to demonstrate that the gang members were or would be motivated to harm [Villalta-Martinez] for any other reason than to extort money from her," and we cannot find, viewing the record as a whole, that a reasonable adjudicator would be compelled to conclude to the contrary. Villalta-Martinez consistently testified in the plural, explaining that both she and her fellow employees were targeted by gang members. Such testimony likely indicates that gang members were targeting all the employees in the store in order to extort money. The threats, albeit terrifying, do not satisfy the statutory requirements for asylum. See Escobar v. Holder, 698 F.3d 36, 38 (1st Cir. 2012) (internal citations omitted) ("Evidence of widespread violence ... affecting all citizens is not enough to establish persecution on a protected ground."). Further, Villalta-Martinez failed to demonstrate whether any of the gang members who threatened her had any knowledge of her relationship with Garcia. See id. at 38 (finding that petitioner failed to provide a connection between family and protected classification where "nothing indicate[d] that the guerrillas specifically targeted [petitioner's] father").

The dissent suggests that remand is appropriate because "neither the BIA nor the IJ ... addressed (or even mentioned) the significant countervailing evidence in the record that suggests that Villalta-Martinez was targeted-at least in part-due to her familial ties to the father of her child." The dissent argues that the IJ and the BIA failed to consider Villalta-Martinez's testimony that the gangs targeted her "because she was the partner of the owner of the store[.]". Relying on Aldana-Ramos v. Holder, 757 F.3d 9, 18 (1st Cir. 2014), the dissent explains that asylum is proper in mixed-motive cases, "so long as one of the statutorily protected grounds is 'at least one central reason' for persecution."

In Aldana-Ramos, the IJ and the BIA erred by stating that the persecution at issue was due to wealth, and therefore could not be attributed to familial relation. Id. The BIA thus failed to consider the possibility of a mixed-motive case. No such error occurred here. The IJ explained that Villalta-Martinez "has not established that one of the reasons she was targeted was because of her relationship with Mr. Garcia." (emphasis added). The IJ and thus the BIA explicitly acknowledged the possibility of a mixed-motive case, but, based on the evidence presented, made a fact-specific determination that Villalta-Martinez had not shown that the persecution was motivated by a family relationship.

The dissent also ascertains that, in light of the "countervailing evidence" as to the nexus requirement, remand is necessary so that the BIA can make additional factual findings. Relying on Aldana-Ramos, the dissent explains that petitioner "put forth credible testimony that creates at least an inference of a 'nexus' between the harm that she suffered and her ties to a person whom she claims is a family member." In Aldana-Ramos, a wealthy family was continually singled out and "followed by members of [the persecuting] gang in unmarked cars" even after they had exhausted their financial resources. Id. As such, the finding that they were targeted because of their wealth, as opposed to their family membership was problematic being that "[n]either the BIA nor the IJ ever addressed this argument." Id. The dissent believes that because Villalta-Martinez presented evidence that she did not have any money when she was persecuted; her lack of money allows an inference *25that she was persecuted on account of her family relationship; and the IJ and the BIA failed to address that argument. However, Villalta-Martinez did not testify that her coworkers, from whom money was also sought, had money or were wealthy. Furthermore, in Aldana-Ramos, the petitioners testified as to why wealth was not a factor that led to their persecution, which created a basis by which to infer that family membership was at least one of the contributing factors for persecution. Here, however, petitioner's testimony did not create the same dichotomy provided by the petitioners in Aldana-Ramos. Villalta-Martinez testified that in addition to targeting her, the gang members were indiscriminately following and threatening all store employees, supporting the BIA's conclusion that the gang members were seeking money without regard for Villalta-Martinez's familial relation. "To reverse the BIA['s] finding we must find that the evidence not only supports [a contrary] conclusion, but compels it." (quoting I.N.S. v. Elias-Zacarias, 502 U.S. 478, 481 n.1, 112 S.Ct. 812, 117 L.Ed.2d 38 (1992) (alterations in original) ).4 We seek to distinguish this case from Aldana-Ramos, not to make our own findings, as the dissent argues, but instead to show that under the deferential standard imposed, we see a variety of bases by which to support the BIA and IJ's determinations.

This case is further distinguished from Aldana-Ramos because the evidence in that case was far more compelling than the evidence here. Multiple family members in Aldana-Ramos testified that their family was targeted for persecution even after their financial resources were exhausted. Id. at 18. In contrast, the only evidence that Villalta-Martinez offered to support her position that she was persecuted because of her family relationship is her own speculation. See Giraldo-Pabon v. Lynch, 840 F.3d 21, 25 (1st Cir. 2016) (finding that substantial evidence supported the conclusion that the nexus requirement for asylum was not met where the petitioner "cite[d] little in the way of nexus evidence other than ... her own belief that another cousin was stabbed because of other family members' involvement in narco-trafficking"); Guerra-Marchorro v. Holder, 760 F.3d 126, 128-29 (1st Cir. 2014) (holding that substantial evidence supported the conclusion that the nexus requirement was not met where the petitioner "presented 'no evidence other than his own speculation' to forge the statutorily required 'link,' " even though the petitioner's testimony had been found credible (quoting Khalil v. Ashcroft, 337 F.3d 50, 55 (1st Cir. 2003) ) ).

Because we find that Villalta-Martinez failed to establish that any harm she suffered was caused by her relationship with Garcia, we need not address whether the BIA erred in determining that the harm she experienced did not rise to the level of persecution. However, one would think that a gang member's specific threat of raping a pregnant women and killing her unborn child if she failed to meet the demands of the gang within 48 hours, after having been threatened at gun point on at least five separate occasions by the same gang, would be the type of harm the Court *26should consider severe enough to rise to the level of persecution.

The dissent spends much time discussing the issue of whether Villalta-Martinez satisfied her burden of showing that the threats she received from the gang could be attributed to inaction by the government of El Salvador. However, she failed to develop her government inaction argument before this Court beyond a vague reference in her brief, without citation to case law or analysis. See Valdez v. Lynch, 813 F.3d 407, 411 n.1 (2016) (holding that an argument is waived where the petitioner "throws in a couple references" to it, but "fails to develop" it). Because government action or inaction is a necessary component of persecution, see Harutyunyan v. Gonzales, 421 F.3d 64, 68 (1st Cir. 2005), Villalta-Martinez's failure to develop that issue before this Court is, on its own, sufficient to sustain the BIA and IJ on this point and to deny her petition for review.

Finally, we note that in making its decision, the BIA explained that "even if the respondent is considered to be in a familial relationship with a man with whom she was in a romantic relationship and with whom she had a child , the respondent has not established a nexus between her past and future fear of harm by gang members and her familial relationship to the man." (emphasis added). While it is well established that the nuclear family constitutes a recognizable social group, neither the BIA nor the IJ found that the petitioner is in fact part of a nuclear family with Garcia. Gebremichael v. I.N.S., 10 F.3d 28, 36 (1st Cir. 1993). Petitioner testified that she was in a relationship with Garcia from 2012 until 2015 when he left El Salvador. Garcia paid rent for petitioner for a period of time and once petitioner became pregnant, she moved into Garcia's home. However, during the pregnancy, Garcia fled El Salvador and petitioner has neither seen nor spoken with him since and Garcia was not listed on the child's birth certificate as the child's father. While we are not in a position to make a finding on this particular issue, we mention these facts solely to demonstrate some of the various obstacles petitioner would face on the remand the dissent seeks. Petitioner's failure to establish a nexus between her persecution and her protected class, and her waiver as to government inaction, are the bases by which we deny her petition for review.

Because Villalta-Martinez cannot satisfy her claim for asylum, we also affirm the BIA's decision denying her claim for withholding of removal. See Escobar, 698 F.3d at 39 ("Statutory withholding of removal under INA § 241(b)(3), 8 U.S.C. § 1231(b)(3), requires an even greater likelihood of persecution than asylum."). Lastly, Villalta-Martinez provides no basis by which the Court should reverse the BIA's decision denying her protection under the CAT, as she failed to argue the point beyond an introductory paragraph in her brief. See Sok v. Mukasey, 526 F.3d 48, 52 (1st Cir. 2008) (finding that petitioner waived her CAT claim appeal when she only referenced the claim in an "introductory assertion").

III. Conclusion

For these reasons, we deny the petition for review and affirm the decision of the BIA upholding the IJ's denial of Villalta-Martinez's application for asylum, withholding of removal, and protection under the CAT.

 Villalta-Martinez originally argued that she was persecuted on account of two statutorily protected grounds, (1) her immediate family membership and (2) people born into lower classes in El Salvador who are able to attain a professional education. Both grounds were rejected by the BIA. In her petition for review, Villalta-Martinez's only challenge is to the BIA's decision with respect to her claimed family membership; therefore, we need not address the merits of Villalta-Martinez's alternative ground for protection. ↵
 Since his illegal reentry into the United States, Garcia has been in federal custody. ↵
 Although the testimony is not entirely clear, it appears that Villalta-Martinez transferred to another store that was also associated with Garcia. ↵
 We acknowledge that the decision by the BIA mistakenly identified Villalta-Martinez as a citizen of Mexico, even though she is from El Salvador. However, at numerous points in its decision, the BIA correctly identified "[t]he respondent, [as] a native and citizen of El Salvador." This error does not warrant remand as it does not demonstrate that the decision by the BIA was either arbitrary or capricious. See Caldero-Guzman v. Holder, 577 F.3d 345, 348 (1st Cir. 2009). ↵
In Part Opinion by Barron
BARRON, Circuit Judge, concurring in part and dissenting in part.
I join the majority in rejecting Rosa Maria Villalta-Martinez's challenge to the denial of her claim under the Convention *27Against Torture. See 8 C.F.R. § 1208.16. I cannot, however, join the majority's decision to uphold the Board of Immigration Appeals' (BIA) determination that her asylum application must be rejected, too.

The main question on which our review of the BIA's asylum ruling turns is a relatively narrow one. After all, the majority agrees, as do I, that the threats that Villalta-Martinez received from a notorious gang in her home country of El Salvador were serious enough to rise to the level of persecution. Thus, the key point of dispute concerns whether we may sustain the BIA's determination that Villalta-Martinez failed to establish the connection between those threats and her claimed familial ties to the father of her child that she was required to establish in order to satisfy what is known as the "nexus" requirement. See Ivanov v. Holder, 736 F.3d 5, 12 (1st Cir. 2013). For, if the BIA's determination regarding the "nexus" requirement may be sustained, then Villalta-Martinez's petition for review must be denied, even if there is merit to her separate challenge to the determination below that she failed to establish that her home country's government was unwilling or unable to address the threat that the gang posed to her.

We are, of course, obliged to sustain the BIA's ruling on the "nexus" issue if it is supported by "substantial evidence." Nikijuluw v. Gonzales, 427 F.3d 115, 120 (1st Cir. 2005). But, we may do so only on the basis of "the record considered as a whole." Id. (internal quotation marks omitted). And here, notwithstanding the majority's contrary conclusion, see Maj. Op. at 23-24, I do not see how we can.

As I will explain, neither the BIA nor the Immigration Judge (IJ), whose findings the BIA adopted, addressed (or even mentioned) the potentially significant countervailing evidence in the record that suggests that Villalta-Martinez was targeted-at least in part-due to her familial ties to the father of her child (a child who was born in the United States and is thus a citizen of this country). Accordingly, consistent with the teaching of Securities & Exchange Commission v. Chenery Corp., 332 U.S. 194, 197, 67 S.Ct. 1760, 91 L.Ed. 1995 (1947), and the course that we followed in Aldana-Ramos v. Holder, 757 F.3d 9, 18 (1st Cir. 2014), I would vacate the BIA's ruling as to Villalta-Martinez's asylum claim and remand for further proceedings.5 And that is because, as I will also explain, once the "nexus" ruling is set aside, there is no other ground on which we may uphold the BIA's affirmance of the IJ's ruling denying her asylum petition.6

I.

With respect to the "nexus" issue, I start by reviewing the key evidence that the IJ and the BIA failed to address, which consists of the testimony that Villalta-Martinez *28gave at her asylum proceeding and which the IJ found to be credible. I then explain why, under our precedent, the IJ's and the BIA's failure to address this evidence precludes us from sustaining the agency's "nexus" ruling.

A.

Villalta-Martinez explained in her testimony that, while she was living in El Salvador but before she was first threatened by the gang, she worked at a store owned by Ever Eliseo Garcia Linares (Garcia), with whom she lived at the time and who is the father of her child. She further testified that Garcia owned a number of stores in El Salvador and that he was paying protection money to a particular gang, the Marasalvatrucha, so that his stores would not be robbed.

Villalta-Martinez explained that, after Garcia fled El Salvador to avoid having to pay off the gang, members of that same gang began to threaten her at the store, even though she had never been personally threatened by members of that gang before. And Villalta-Martinez went on to describe how she eventually moved to a different one of Garcia's stores in order to escape the gang but that the threats from members of that gang did not stop. Rather, she recounted, members of the gang that Garcia had been paying off, and that had threatened her at the first store after he had left the country, simply followed her to that new store and threatened her there.

Villalta-Martinez also testified that each time the gang members came into this second store while she was working there, they "demande[ed] money from the store and then they demanded directly money from me." Villalta-Martinez added that the gang targeted her at that store because she "was the partner of the owner of the store[.]" In fact, she went on to note that she could not have been targeted by the gang members at this store because she had money, as she testified that she had none.

To be sure, Villalta-Martinez did testify that she was not the only store employee whom the gang members threatened. But that acknowledgement hardly suffices to demonstrate that the gang members did not target her "on account of" her ties to Garcia. Even if the gang members were clearly interested in acquiring money from those they threatened at the stores, we have long recognized that "asylum is still proper in mixed-motive cases even where one motive would not be the basis for asylum, so long as one of the statutorily protected grounds is 'at least one central reason' for the persecution." Aldana-Ramos, 757 F.3d at 18 (quoting 8 U.S.C. § 1158(b)(1)(B)(i) ) (emphasis added). Thus, notwithstanding this aspect of Villalta-Martinez's testimony, the gang members may have been partly motivated to target Villalta-Martinez because of her ties to Garcia as his "partner" despite the fact that they also may have wanted money from the store or its employees.

Significantly, the government in cross-examining Villalta-Martinez never challenged her contention that the gang members threatened her, at least in part, because of her relationship with Garcia and not solely in order to obtain money either from her or from the store. That is perhaps because, the record indicates, the government failed to realize that she intended to argue, based on her testimony as to her living arrangement with Garcia and her child with him, that she was part of a family with Garcia for the purposes of establishing her membership in a "social group."

In fact, after Villalta-Martinez completed her testimony, the government initially *29argued that the IJ should deny the asylum claim on the ground that "girlfriends of shop owners in El Salvador" did not constitute a cognizable "social group" under the asylum statute, thereby rendering the "nexus" issue beside the point insofar as the government's "social group" argument had merit. The government made no argument at that point in the asylum proceedings that the gang members' threats were not partly motivated by, as Villalta-Martinez had testified, the fact that she was Garcia's "partner."

The government shifted course, however, after Villalta-Martinez's counsel clarified that the petitioner's asserted "social group" was the family that Villalta-Martinez claimed to have established with Garcia. The government at that point argued for the first time that Villalta-Martinez's testimony was insufficient to demonstrate the required "nexus" between the threats that she received and her ties to Garcia.

By then, though, the government had done nothing to undermine the portions of Villalta-Martinez's testimony in which she had asserted, credibly, that the gang had not only threatened her at the first store where she had been working but also had gone on to follow her to the second of Garcia's stores. Nor had the government done anything as of that point to undermine her testimony that the gang members directly targeted her there because she was Garcia's "partner." Nor, finally, had the government done anything by that point to undermine Villalta-Martinez's contention in her testimony that she had no money of her own at the time that she was so targeted.

Thus, as the case comes to us, the record contains uncontradicted, credible testimony from Villalta-Martinez that would appear to give rise to an inference that the gang's threats were motivated at least to some extent by her claimed familial ties to Garcia. Nevertheless, in finding that Villalta-Martinez had failed to meet her burden to satisfy the "nexus" requirement, neither the IJ nor the BIA discussed (or even referenced) any of the portions of her testimony that I have just described.

The IJ simply concluded summarily and categorically that "the evidence was not that [Villalta-Martinez] was targeted because of Mr. Garcia, but that she was targeted by gangs each and every time because they wanted money." (Emphasis added.) The BIA similarly stated in conclusory and categorical fashion that there "is insufficient evidence in the record to demonstrate that the gang members were or would be motivated to harm the response [sic] for any other reason than to extort money from her." (Emphasis added.) And, in doing so, the BIA claimed to be adopting the opinion (and thus the findings) of the IJ.

B.

The key question, then, is whether these rulings on the "nexus" issue may be sustained despite the BIA's and IJ's failure even to mention-let alone to explain away-the evidence that Villalta-Martinez offered that potentially would support her main argument as to why the record showed that there was a "nexus" between the gang members' threats and her membership in a statutorily protected "social group." And the answer to that question, as I will explain, is that, in light of our decision in Aldana-Ramos, these "nexus" rulings may not be sustained.

In Aldana-Ramos, the petitioners premised their asylum claims on the ground that the harm that they had suffered at the hands of a gang in Guatemala was "on account of" of their ties to their father and thus their membership in a protected "social group." Id. at 13-14. They contended *30that this group was their nuclear family. Id. at 13. The BIA rejected that contention. Id. at 18.

The petitioners contended on appeal in Aldana-Ramos that the BIA erred in two ways in so ruling. The petitioners argued that the BIA had wrongly concluded that, even if they showed that their familial ties to their father were "at least one central reason" why they were targeted by the gang, those ties could not satisfy the "nexus" requirement because the petitioners had not shown that their father had been targeted by the gang based on a statutorily protected ground. See id. at 18. The petitioners also argued that the BIA's ruling that wealth alone explained their targeting by the gang "was unsupported by the record," given that the petitioners had credibly testified that they had "exhausted all of their own and their family's financial resources in trying to raise the money to ransom their father [from the gang]," but continued to be "followed by [gang] members ... even after their father's funeral." Id. And, to back up that contention, the petitioners pointed to their testimony that "unmarked cars" followed them after their father's funeral, although we did not say in Aldana-Ramos that the petitioners had claimed in their testimony that the petitioners knew who precisely was in those cars, that the persons in the cars said anything to indicate why they were following the petitioners, or that the persons in the cars knew that the petitioners had exhausted all of their financial resources. Id. at 13.

We then ruled for the petitioners on both of their asserted grounds for overturning the BIA's "nexus" ruling. Id. at 19. We explained that the BIA had erred by failing to consider the possibility that the "nexus" requirement could have been satisfied by a showing that the gang members were partly motivated to target the petitioners due to their familial ties to their father, even if the petitioners' wealth also played a role in their being targeted by the gang and even if their father had not himself been targeted for any reason other than his wealth. Id. We also separately explained that the BIA's "nexus" finding that the petitioners' wealth alone explained the targeting could not be sustained, even under the deferential substantial evidence standard. Id. And we did so because we explained that the BIA had overlooked the critical evidence regarding the unmarked cars and the petitioners' having exhausted their financial resources paying for their father's ransom, given that this evidence sufficed to create an inference of family-based targeting that the BIA was obliged to address. Id. at 18-19.

In light of Aldana-Ramos's separate substantial evidence holding, I see no justification for reaching a different conclusion with respect to whether substantial evidence supports the BIA's "nexus" ruling in this case. Here, too, the asylum seeker has put forth credible testimony that creates at least an inference of a "nexus" between the harm that she suffered and her ties to a person whom she claims is a family member. Here, too, that evidence takes the form of the asylum seeker's credible testimony that she was followed by the gang that menaced her even after she took steps to protect herself from it and that the gang members sought her out in particular because of her ties to the person she claims to be a family member. Here, too, the asylum seeker contends that these threats were directed at her by the gang even though she had no money to hand over to the gang. And yet, here, too, the BIA (like the IJ) failed to address or even mention that evidence of family-status-based targeting in concluding that the evidence showed that the asylum seeker had not been harmed "on account of" her familialties *31and that instead she had been targeted solely for financial reasons.

In concluding that, despite the seeming similarities between Aldana-Ramos and this case, Aldana-Ramos is not controlling, the majority offers two grounds for drawing a distinction. But I am not persuaded by either one.

First, the majority rightly points out that in Aldana-Ramos, unlike in this case, the BIA refused to acknowledge the possibility that the "nexus" requirement may be satisfied by showing that the perpetrators of threats had mixed motives, only one of which was to target the asylum-seekers on account of their membership in a statutorily protected group (namely, the nuclear family that they shared with their father). Id. at 18 ; Maj. Op. 24-25. But, as noted above, Aldana-Ramos also ruled, wholly apart from that legal error, that the BIA's "nexus" ruling that wealth alone explained the petitioners' targeting could not be sustained because that ruling was not supported by substantial evidence. Id. And Aldana-Ramos came to that separate conclusion about whether substantial evidence supported the "nexus" ruling precisely because the BIA at no point addressed the portions of the petitioners' testimony concerning the men in the unmarked cars and the petitioners' own lack of financial resources that gave rise to an inference that the petitioners were targeted by the gang due to their familial ties to their father. Id. Thus, Aldana-Ramos's recognition that the BIA made a legal error concerning whether motives may be mixed does nothing to diminish the relevance to the case before us of Aldana-Ramos's independent ruling rejecting the BIA's substantial evidence ruling for failing to account for countervailing evidence of family-based targeting.

Second, the majority contends that Aldana-Ramos is distinguishable because the evidence of family-based targeting was much more compelling there than it is here, as Villalta-Martinez's evidence of such targeting in the end amounts to little more than her own speculation about the gang members' motives. Maj. Op. 24-25. But, even if the evidence of family-based targeting is weaker in this case than it was in Aldana-Ramos, the key point is that the evidence in this case is still strong enough to "create[ ] an inference" of family-based targeting that the BIA must actually address. 757 F.3d at 18 ; see also id. at 14 n.2 ("Absent a holding by the [agency] ... or some explanation rebutting this inference," the agency's conclusion cannot be upheld).

Villalta-Martinez credibly testified that she was singled out by the Marasalvatrucha gang because she was Garcia's partner. She also testified that she knew that Garcia had been subjected to threats by that same gang while she was already working at his store. It thus hardly requires a great inferential leap to conclude from her credible testimony as to these points that she had a more than conjectural basis for believing that the gang members who she testified targeted her knew of her ties to Garcia when they followed her to a second of Garcia's stores and then directly targeted her there after having targeted other store employees.7

*32Moreover, whether one agrees or not with that assertion, in upholding the BIA's ruling on the ground that Villalta-Martinez's evidence of family-based targeting amounts merely to her own speculation and thus does not suffice to show the required "nexus," the majority is not relying on any finding that the BIA or the IJ, whose findings the BIA purported to adopt, actually made. Neither the BIA nor the IJ even mentioned the evidence of family-based targeting on which Villalta-Martinez primarily relied, let alone explained that such evidence was too speculative.

Nor do the "speculation" cases on which the majority relies, see Maj. Op. 24-25, indicate that we must infer that the BIA and the IJ rejected Villalta-Martinez's testimony that she was targeted because she was Garcia's partner on the ground that such evidence was too speculative. None of those cases concerned remotely comparable evidence of family-based targeting to that put forward by Villalta-Martinez, and thus it is by no means clear that the BIA or the IJ would have been required to find the evidence too speculative.8

Finally, I note that the government, in the part of its brief addressing the "nexus" issue, does not reference any of the "speculation" cases on which the majority relies to sustain the "nexus" rulings. Nor does the government even argue-as the majority now posits-that the reason that Villalta-Martinez's evidence of family-based targeting does not suffice is that it was too speculative to be credited. Instead, the government, like the IJ and the BIA, simply makes no reference to that evidence at all in arguing that the "nexus" rulings must be sustained.9

*33As a result, it seems to me that the majority is unavoidably upholding the "nexus" rulings on a ground of its own making. But, that we may not do, as our job is to review the reasoning of the agency, not to supply it. See Chenery Corp., 332 U.S. at 200, 67 S.Ct. 1760. Thus, per Aldana-Ramos, I would require the BIA to do what it has thus far failed to do-grapple in a reasoned way with the uncontradicted testimony that Villalta-Martinez credibly offered in order to show that she endured the gang's threats at least in part because she was Garcia's "partner." See Aldana-Ramos, 757 F.3d at 18 n.7 ("[T]he government suggests that the BIA could infer that the ... gang subjectively believed that petitioners still had access to more money. That approach, not articulated by the BIA, fails because the BIA never actually drew the inference.").

II.

In consequence of my view of the "nexus" issue, I must now address one last issue that the majority need not reach. As the government notes, the BIA adopted the IJ's decision, and the IJ ruled not only that Villalta-Martinez lost on the "nexus" issue but also that she had failed to meet her burden of showing that the threats that she received from the gang could be attributed to "action or inaction" by the government of El Salvador. See Harutyunyan v. Gonzales, 421 F.3d 64, 68 (1st Cir. 2005) ; 8 U.S.C. § 1101(a)(42). Thus, before we may vacate and remand the petition for review, we must address the IJ's ruling on the "action or inaction" issue.

I do not believe, however, that we may uphold the agency's ruling on the basis of the IJ's ruling on the "action or inaction" issue. And that is so for reasons that are similar to those that lead me to conclude that we may not sustain the agency's "nexus" ruling.

To show the requisite "action or inaction" by the government of El Salvador, Villalta-Martinez put forward the following evidence: a report by the Organisation for Economic Co-operation and Development (OECD) on issues affecting youth in El Salvador and a Reuters article on the relationship between gang violence and youth migration. This evidence may not be enough, in the face of a contrary agency finding, to "compel" the conclusion that she has shown the required tie between the gang's threats and the government of El Salvador's "action or inaction." Touch v. Holder, 568 F.3d 32, 39 (1st Cir. 2009). The IJ, however, did not address either the report or the article in ruling against Villalta-Martinez on this issue. Instead, the IJ's decision merely notes that Villalta-Martinez failed to report to the authorities in El Salvador the incidents she endured at the hands of the gang that she now contends constituted past persecution.

We have never held, however, that asylum seekers must have sought assistance from authorities in order for them to be able to prove that they have suffered past persecution. To the contrary, we have held that "the failure by a petitioner to make ... a report is not necessarily fatal to a petitioner's case if the petitioner can demonstrate that reporting private abuse to government authorities would have been futile." Morales-Morales v. Sessions, 857 F.3d 130, 135 (1st Cir. 2017). Thus, the ground the IJ gave for ruling against Villalta-Martinez on this issue cannot suffice.

Moreover, the agency has failed to address (or even mention) the countervailing *34evidence that casts doubt on the government of El Salvador's ability to control gang activity within its borders-namely, the OECD report and Reuters article. And that failure is problematic because, while neither the report nor the article directly addresses the police's ability to prevent gang violence, the OECD report does conclude that government anti-gang initiatives are "ineffective[ ]," and the Reuters article notes that "[e]ntire neighborhoods in El Salvador are controlled by street gangs." Cf. Hernandez-Avalos v. Lynch, 784 F.3d 944, 953 (4th Cir. 2015) (holding that government of El Salvador was "unwilling or unable" to control gang violence). Thus, given that we may not sustain an agency's decision on the basis of reasons other than those that the agency provides, Chenery Corp., 332 U.S. at 196, 67 S.Ct. 1760 ; see Aldana-Ramos, 757 F.3d at 18 n.7,10 the agency should be required to reconsider this aspect of the asylum ruling, too.

III.

For the foregoing reasons, I respectfully dissent as to Villalta-Martinez's asylum claim.""")

# Case 5
add_case("""Aguilar de Guillen v. Sessions
Court of Appeals for the First Circuit

Citations: 902 F.3d 28
Docket Number: 17-2095P
Judges: Torruella, Lipez, Thompson
Opinion
Authorities (22)
Cited By (21)
Summaries (3)
Similar Cases (49.8K)
PDF
Headmatter
Irma Yolanda AGUILAR-DE GUILLEN, et al., Petitioners,
v.
Jefferson B. SESSIONS III, Attorney General of the United States, Respondent.
No. 17-2095
United States Court of Appeals, First Circuit.
August 27, 2018
Carlos E. Estrada, Boston, MA, Ashley M. Edens, and Estrada Law Office on brief for petitioner.
Jane T. Schaffner, Trial Attorney, Office of Immigration Litigation, Civil Division, United States Department of Justice, Chad A. Readler, Acting Assistant Attorney General, Civil Division, and Paul Fiorino, Senior Litigation Counsel, Office of Immigration Litigation, on brief for respondent.
Before Torruella, Lipez, and Thompson, Circuit Judges.
Combined Opinion by Thompson
THOMPSON, Circuit Judge.
Petitioner, 1 Irma Yolanda Aguilar-De Guillen, seeks judicial review of a Board of Immigration Appeals ("BIA") opinion affirming an Immigration Judge's ("IJ") decision denying her asylum relief, withholding of removal under the Immigration and Nationality Act ("INA"), and protection pursuant to the Convention Against Torture Act ("CAT") and ordering her removed. She claims the BIA erred in affirming the IJ's finding that: (1) she did not suffer past persecution on account of a protected ground; (2) she did not have a well-founded fear of future persecution; and (3) she was not entitled to protection under CAT. 2 Finding no merit to her arguments, we affirm.

A. BACKGROUND

1. Life in El Salvador 3

Petitioner was born in El Salvador in 1985. In 2006, she married Miguel Ángel and the pair had two children (who, as minors, are co-petitioners in this case). In El Salvador, she owned and operated a fruit and vegetable store with her husband. On several occasions, while her husband was off working as a taxi driver (his second job), gang members threatened to kill them unless their business paid monthly "rent" to the respective gang. The gang threatened to throw a grenade into her *31 home if she refused to pay. The gang members also informed Petitioner that they knew where her children went to school and she interpreted this as an additional threat. While four of the death threats were made via hand-written notes between December 2012 and January 2013, she also received several phone calls during that time with similar threats. She reported these incidents to her husband, who in turn reported them to the police. The police informed the two that they would "look into it" and advised Petitioner to turn off her telephone to avoid future threating calls. Once she reached out to a private detective about these threats and he agreed to be on the lookout at the store, the gang ceased making any threats.

While no one on Petitioner's side of the family had suffered any gang violence, both her husband's nephew and his brother were killed by a gang after they refused to join. In April 2013, her husband came to the United States, and in June 2014, Petitioner followed with their two children. She traveled to the United States through the U.S./Mexico border without inspection. 4

Upon Petitioner's entry to the United States, Petitioner was apprehended and detained. Thereafter, immigration officials filed a notice to appear alleging removability pursuant to § 212(a)(6)(A)(i) of the INA. Petitioner conceded removability and later applied for relief in the form of asylum, withholding of removal under the INA, and protection under CAT. Petitioner cited the several gang death threats she had received while living in El Salvador as the cause of her traveling to the United States and why she sought relief from removal.

2. The IJ Hearing

A hearing was held before the IJ on her application in March 2017, wherein Petitioner testified about her life in El Salvador. In support of her request for relief, in addition to her own testimony, Petitioner submitted a country condition report highlighting the violence in El Salvador relating to gangs and the police's ongoing struggle to manage the situation.

After the hearing, the IJ denied her application for relief. Although the IJ found Petitioner credible, consistent, and "extremely sympathetic," he found that she had not suffered past persecution or held a well-founded fear of future persecution on a protected ground as necessary to qualify for asylum relief. As to a well-founded fear of future persecution, the IJ noted that she had also failed to prove that any persecution was related or connected to her membership in a protected group, "as the crimes [she] suffered ... appear[ed] to be widespread according to the country conditions." The IJ found the purpose behind the death threats was extortion, and that Petitioner had failed to present any evidence that would support an inference that any future persecution would be on account of her familial relationship. 5 The IJ also found that Petitioner had failed to show government involvement-either through its inability or unwillingness to protect her from harm. Because Petitioner was unable to establish asylum, she necessarily failed to meet the requirements for withholding of removal under INA. Lastly, the IJ also denied her *32 CAT relief on the basis that she had not proved that she would likely face torture at the hands of the El Salvadoran government if she were to return. The IJ ordered Petitioner removed.

3. Appeal to BIA

Petitioner timely appealed to the BIA, which agreed with the IJ and therefore dismissed her appeal. The BIA held that "the record in this case [did] not indicate that the [petitioner's] family membership, or her familial relationship to her husband, was or will be at least one central reason for the harm she suffered or may suffer upon her return to El Salvador"-rather, the record demonstrated that the gang members were motivated by the desire to increase their wealth through extortion. The BIA also offered two reasons for rejecting Petitioner's new claim that she had a well-founded fear of future persecution on account of being a member of another particular social group: "single mothers who are living without male protection and cannot relocate elsewhere in the country." First, it did not find that this group was "cognizable as a particular social group" pursuant to asylum law because it was not defined with particularity; second, to the extent her argument regarding future persecution related to a general fear of gang violence, that too was not a recognizable ground for asylum. The BIA then quickly disposed of her withholding of removal claim before discussing her CAT claim. Like the IJ, the BIA found that because Petitioner had not met her burden for asylum, it followed she had not satisfied the higher standard of a clear probability of persecution on account of a protected ground as required for withholding of removal. As for her CAT claim, the BIA determined that Petitioner had not established "that she is more likely than not to be tortured in her country, by or at the instigation of or with the consent or acquiescence ... of a public official or other person acting in an official capacity." An order subsequently followed dismissing her appeal, and she now seeks review of that dismissal by this Court. 6

B. DISCUSSION

Before us, Petitioner assigns three errors to the BIA's decision, specifically, that it erred in affirming the IJ's finding that: (1) she did not suffer past persecution on account of being a member of a protected class; (2) she did not have a well-founded fear of future persecution (irrespective of any past persecution); and (3) she was not entitled to protection under the CAT.

1. Standard of Review

Where, as here, "the BIA adopts and affirms an IJ's decision, we review the IJ's decision to the extent of the adoption, and the BIA's decision as to any additional ground." Sunoto v. Gonzales , 504 F.3d 56 , 59-60 (1st Cir. 2007) (internal quotation marks, citation and brackets omitted). We review the IJ's findings of fact relied on by the BIA in support of its decision for substantial evidence, meaning we accept the findings "as long as they are supported by reasonable, substantial and probative evidence on the record considered as a whole." Singh v. Holder , 750 F.3d 84 , 86 (1st Cir. 2014) (internal quotation marks and citation omitted). Only where the record *33 compels a contrary outcome will we reject the IJ's findings. Thapaliya v. Holder , 750 F.3d 56 , 59 (1st Cir. 2014).

Moreover, a BIA conclusion regarding the definition and scope of the statutory term "particular social group" is a purely legal determination that we review de novo. Castañeda-Castillo v. Holder , 638 F.3d 354 , 363 (1st Cir. 2011) (citation omitted). We do, however, give deference "to the interpretation given the term 'social group' by the BIA even if we conclude that the term is susceptible to more than one permissible interpretation." Elien v. Ashcroft , 364 F.3d 392 , 397 (1st Cir. 2004) (citation omitted).

2. Asylum Relief

A petitioner may be eligible for asylum if he or she can establish persecution on account of a legally protected ground in one of two ways: (1) past persecution or (2) a well-founded fear of future persecution. Albathani v. INS , 318 F.3d 365 , 373 (1st Cir. 2003) ; 8 U.S.C. § 1158 (b)(1) ; § 1101(a)(42)(A); 8 C.F.R. § 208.13 . "[R]ace, religion, nationality, membership in a particular social group, or political opinion" are grounds specifically enumerated in asylum law. Olujoke v. Gonzáles , 411 F.3d 16 , 21 (1st Cir. 2005) (quoting 8 U.S.C. § 1101 (a)(42)(A) ). "To show that the circumstances the applicant endured constitute persecution for purposes of asylum relief, she must show 'a certain level of serious harm (whether past or anticipated), a sufficient nexus between that harm and government action or inaction, and a causal connection to one of the statutorily protected grounds.' " Martínez-Pérez v. Sessions , 897 F.3d 33 , 39 (1st Cir. 2018) (quoting Carvalho-Frois v. Holder , 667 F.3d 69 , 72 (1st Cir. 2012) ).

If a petitioner can prove she suffered past persecution while in her home country, a rebuttable presumption that her fear of future persecution is well-founded is triggered. 7 8 C.F.R. § 208.13 (b)(1) ; see Harutyunyan v. Gonzales , 421 F.3d 64 , 67 (1st Cir. 2005). "Without past persecution, an asylum applicant can still show a well-founded fear of future persecution by showing that he or 'she genuinely fears future persecution and that her fears are objectively reasonable.' " Martínez-Pérez , 897 F.3d at 39 (quoting Carvalho-Frois , 667 F.3d at 72 ) (citation omitted). In either case, however, "[a]n inability to establish any one of the three elements of persecution will result in a denial of [the] asylum application." Carvalho-Frois , 667 F.3d at 73 .

a. Past Persecution

Petitioner challenges all three grounds by which the IJ and the BIA rejected her claim of past persecution: severity, nexus, and government involvement. However, because Petitioner must establish every element of her claim to be entitled to relief, see Carvalho-Frois , 667 F.3d at 72 , we begin and end our discussion with the nexus prong. Id. (For simplicity's sake, this Court proceeds directly to petitioner's weakest argument.)

Petitioner maintains that she was persecuted because of her familial relationship to her husband and the BIA erred by not *34 concluding that it was clearly erroneous for the IJ to find that she did not establish past persecution on account of such grounds. 8 We will assume without deciding that the harm Petitioner suffered constituted past persecution and that her membership in her Husband's family constitutes a cognizable social group. See Romilus v. Ashcroft , 385 F.3d 1 , 6 (1st Cir. 2004) (because the issue was not dispositive, we assumed without deciding that the group the petitioner was a member of was a political organization).

Petitioner's protected ground needs to be "at least one central reason" for the persecution she suffered for asylum purposes. Aldana-Ramos v. Holder , 757 F.3d 9 , 18 (1st Cir. 2014) (quoting 8 U.S.C. § 1158 (b)(1)(B)(i) ). "[A]sylum is still proper in mixed-motive cases even where one motive would not be the basis for asylum, so long as one of the statutory protected grounds is 'at least one central reason' for the persecution." Id. ; accord Villalta-Martinez v. Sessions , 882 F.3d 20 , 28 (1st Cir. 2018). In other words, "the presence of a non-protected motivation does not render an applicant ineligible for refugee status." Aldana-Ramos , 757 F.3d at 19 . However, a petitioner's "speculation or conjecture, unsupported by hard evidence is insufficient to establish nexus." Ruiz-Escobar v. Sessions , 881 F.3d 252 , 259 (1st Cir. 2018) (internal quotation marks and citation omitted).

Petitioner's claim of past persecution fails because she does not point to any evidence to support an inference that her membership in her husband's family was at least one of the reasons she suffered any harm, much less does she point to record evidence compelling us to disagree with the BIA's affirmance of the IJ's findings. See Jianli Chen v. Holder , 703 F.3d 17 , 21 (1st Cir. 2012) ("[W]e will reverse only if the record is such as to compel a reasonable factfinder to reach a contrary determination.") As the BIA noted, the only reasonable inference to be made by the evidence Petitioner presented at the hearing before the IJ is that the gang members targeted Petitioner and her family to increase their wealth through extortion. Petitioner introduced no direct (or circumstantial) evidence that the gang's threats had anything to do with her membership in her husband's family. See Sosa-Perez v. Sessions , 884 F.3d 74 (1st Cir. 2018) (The petitioner "offer[ed] no direct evidence to support her assertion that the assailants knew that she was a member of the family that she alleges they were targeting, let alone that they attacked her on that basis.")

While Petitioner maintains that both the IJ and BIA failed to properly consider "mixed motive" persecution, we disagree. A review of both decisions quickly reveals that they considered the possibility of her familial relationship being only one central cause of the persecution, but both concluded Petitioner had failed to present any evidence to support her allegation. The IJ specifically acknowledged "that there often can be mixed motives and that family can serve as a cognizable particular social group." 9 Meanwhile, the BIA also acknowledged *35 that family membership can constitute a social group but that here, the evidence showed that "gang members targeted [Petitioner] for no other reason than to increase their wealth through extortion." Nothing in the IJ's or BIA's decisions indicates that either the IJ or the BIA felt that, once the IJ found the gang was motivated by increasing its own wealth, the IJ was precluded from finding that they also targeted Petitioner due to her familial relationship (or, presumably, any other reason) as she maintains. We agree with Petitioner that the gang could have had more than one motive that would have resulted in Petitioner meeting the nexus prong, but we also see nothing in the record to compel such conclusion. Accordingly, Petitioner failed to meet a necessary requirement to establish past persecution.

b. Future Persecution

Next, Petitioner argues that irrespective of her ability to establish past persecution, she has established a well-founded fear of future persecution if she were to return to El Salvador. In addition to arguing she fears persecution on the basis of her familial relationship to her husband, 10 she also adds that if she were to return to El Salvador, she would be a single mother without the protection of a male figure and unable to relocate within the country, and that this is a protected ground.

A party seeking asylum " 'based on 'membership in a particular social group' must establish that the group is: (1) composed of members who share a common immutable characteristic, (2) defined with particularity, and (3) socially distinct within the society in question.' " Paiz-Morales v. Lynch , 795 F.3d 238 , 244 (1st Cir. 2015) (quoting Matter of M-E-V-G- , 26 I&N Dec. 277 , 237 (BIA 2014) ). The BIA concluded that Petitioner failed to establish both prongs two and three in her proposed group of "single mothers who are living without male protection and cannot relocate elsewhere in the country."

While Petitioner attempts to distinguish her case from the facts and holding of Perez-Rabanales v. Sessions , 881 F.3d 61 , 66 (1st Cir. 2018), wherein we found that the proposed social grouping "Guatemalan women who try to escape systemic and severe violence but who are unable to receive official protection" failed to satisfy the particularity and social distinctiveness requirements, her discussion falls short. After outlining the facts and holding in Perez-Rabanales , she makes a boilerplate assertion that "her social group of single mothers lacking male protection and unable to relocate is socially distinct, easily perceived by society, and not defined by the persecution of its members" without telling us exactly how that is the case. Petitioner does not provide us with a meaningful discussion of how her proposed group satisfies the particularity and social distinctiveness requirements any more than the petitioner in Perez-Rabanales . Instead, she points to two things broadly to support her argument: (1) her "credible testimony", and (2) "the numerous corroborating documents submitted by [her] evidencing the pervasive and systemic violence against women, and in particular single mothers, in El Salvador." However, Petitioner's reliance on her testimony and corroborating documents is *36 misplaced because the question is whether her proposed social group generally-not her circumstances specifically-meet the requirements of a "particular social group" as a matter of law. See Elien , 364 F.3d at 397 .

In any event, our de novo review yields us to the same outcome we reached in Perez-Rabanales . Even assuming the proposed social group of "single mothers without the protection of a male figure and unable to relocate in their country" satisfies prong one, i.e., it is composed of members who share a common immutable characteristic-it nevertheless fails prong two: being defined with particularity. Like the proposed group in Perez-Rabanales , "[t]he amorphous nature of [Petitioner's] sprawling group precludes determinacy and renders the group insufficiently particular." Id. at 65. Her proffered social group is overly broad and potentially encompasses all single mothers in El Salvador who may find themselves unable to relocate in the country. See id. Moreover, exactly what constitutes "without male protection" is an "open question," and possibly a subjective determination. See Paiz-Morales , 795 F.3d at 244-45 . Accordingly, Petitioner's attempt to qualify for asylum based on her membership in a social group fails because she does not meet the particularity requirement. 11

c. Protection under the CAT

Lastly, Petitioner argues that, since the primary reason her asylum application was denied was because the BIA affirmed the IJ's finding that she did not meet the "nexus" requirement and there is no requirement that the persecution be on the basis of a protected ground under CAT, she should have been granted this form of relief. She argues that the IJ did not properly consider her claim of relief under CAT because it failed to consider the voluminous country conditions reports she submitted depicting "the rampant nationwide use of torture by ... gangs."

Pursuant to Article 3 of CAT, the United States has an obligation under international law not to "expel, return (refouler) or extradite" a person to a country where there are "substantial grounds for believing that he [or she] would be in danger of being subjected to torture." 8 C.F.R. § 208.16 (c)(4). An applicant seeking relief must show that he or she is "more likely than not" to be tortured if removed to a particular country. 8 C.F.R. § 208.16 (c)(4). The torture must be "inflicted by or at the instigation of or with the consent or acquiescence of a public official or other person acting in an official capacity." 8 C.F.R. § 208.18 (a)(1).

Contrary to Petitioner's assertion, the BIA did not reject her asylum claim because of a lack of "nexus." Rather, the BIA affirmed the IJ's finding that Petitioner had not shown that she is more likely than not to be tortured in El Salvador. As was the case in the past-persecution discussion, Petitioner wholly fails to point to any record evidence that would compel us to reach a different outcome. Instead, Petitioner takes issue with the IJ's decision because it cites 2008 and 2012 opinions 12 -which Petitioner characterizes as dated. But our review is limited to "the reasoning provided by the [BIA]." Mejia v. Holder , 756 F.3d 64 , 69 (1st Cir. 2014). The BIA noted the absence of record evidence indicating a likelihood that a Salvadoran official would acquiesce in any torture inflicted upon Petitioner *37 by gang members, and Petitioner has not articulated how the BIA got it wrong. Our review of the record before us indicates the BIA's decision is well supported, and it does not compel us to reach a different outcome.

C. CONCLUSION

For the foregoing reasons, we deny the petition for judicial review.""")

# Case 6
add_case("""Sunarto Ang v. Holder
Court of Appeals for the First Circuit

Citations: 723 F.3d 6, 2013 WL 3466210, 2013 U.S. App. LEXIS 13926
Docket Number: 12-1684
Judges: Lynch, Howard, Thompson
Opinion
Authorities (12)
Cited By (20)
Summaries (1)
Similar Cases (39.2K)
PDF
Headmatter
SUNARTO ANG, Petitioner, v. Eric H. HOLDER, Jr., Attorney General, Respondent.

No. 12-1684.

United States Court of Appeals, First Circuit.

July 10, 2013.

*8 Wei Jia and Law Office of Wei Jia on brief for petitioner.

Janette L. Allen, Trial Attorney, Office of Immigration Litigation, Civil Division, U.S. Department of Justice, Stuart F. Delery, Principal Deputy Assistant Attorney General, Civil Division, and Stephen J. Flynn, Assistant Director, Office of Immigration Litigation, on brief for respondent.

Before LYNCH, Chief Judge, HOWARD and THOMPSON, Circuit Judges.
Combined Opinion by Howard
HOWARD, Circuit Judge.
Sunarto Ang and his wife Tuti Erlina, who are citizens of Indonesia, seek review of a final order from the Board of Immigration Appeals (BIA). Because no record evidence compels a different result than that espoused by the Immigration Court and upheld by the BIA, the petition for review is denied.

*9 I. Background

Ang and Erlina entered the United States on March 29, 2007 as nonimmigrant visitors with authorization to remain in the United States until September 28, 2007. They overstayed their visas, and in late 2007 they applied to the Department of Homeland Security (DHS) for asylum. In May 2008, DHS filed Notices to Appear with the Immigration Court, charging Ang and Erlina with removability under Section 237(a)(1)(B) of the Immigration and Nationality Act, 8 U.S.C. § 1227(a)(1)(B), for remaining in the United States for longer than permitted. Ang and Erlina conceded removability, renewed their application for asylum, and applied for withholding of removal and protection under the Convention Against Torture. They both testified before an Immigration Judge (IJ), who found their testimony credible. We summarize this testimony below.

Ang was born in Indonesia to parents of Chinese ethnicity, and he followed Buddhism until his adulthood. Ang's father owned a store where indigenous Muslims would demand money. If Ang's father did not pay them, they would rummage the store. In 1982, these Muslims beat Ang's father. Because of this beating, Ang's mother fell sick. 1 Ang's father reported the incident to the authorities, but "the police didn't come."

In 1988, Ang converted to Christianity. That same year he met Erlina, and they were married in 1990. Because Erlina was Muslim, Ang converted to Islam, but he was only "pretending" so that he could marry her. During their marriage, Ang and Erlina attended church together. Although they were not baptized at the time, they considered themselves Christians. Since 1988, Ang has traveled outside of Indonesia and returned at least three times, following advice from friends that such travel would make it easier to obtain a visa to enter the United States. Erlina joined Ang on one of these trips, to Malaysia. Ang also traveled alone to Australia, but he did not apply for asylum there because he "didn't feel Australia was the right place for [him]." Ang and Erlina have visas to enter South Korea as well, but they did not travel there.

In 1998, Ang and his father both owned stores that were burned in an anti-Chinese riot in Jakarta. Ang tried to flee on a motorcycle, but the mob stopped him. They took off his helmet and said, "Hey, this is Chinese. Finish him. Finish him." Ang was stabbed in the lower back and pretended to be unconscious. Later, a man helped Ang to the hospital, where he received stitches. Ang notified the police, who gave him a written report and later told him that they could not find the perpetrators. Ang's father was so shocked by the riots that he died about seven months later. Since 1998, nothing has happened to Ang or his family. His family remained in Indonesia after he left.

Erlina's family found out that she had converted to Christianity. In December 2006, shortly after their discovery, her family members beat, stepped on, and slapped Erlina, calling her an "undevoted child." Erlina's Muslim neighbors saw the incident but did nothing. Erlina did not call the police because she thought it would be wasteful, given that the majority of Indonesia's population is Muslim.

Ang and Erlina entered the United States in March 2007. They initially settled in Philadelphia and eventually moved to New Hampshire. Erlina's family calls her to threaten her into returning to Islam, and they often say that they want to *10 kill her. Erlina feels that she will not get protection from the police if she returns to Indonesia because the police are sometimes afraid of Muslim groups. One of these groups, to which her family belongs, is Mohammed Deif, which terrorizes Christians.

After hearing this testimony, the IJ rejected Ang and Erlina's application for asylum, stating that the 1982 beating of Ang's father and the 1998 riot did not amount to persecution and did not involve government officials. The IJ said that the riot was not a "persecutory incident targeting [Ang]" because he "happened to get caught up in the riot." The IJ also held that Erlina's single beating by her family did not rise to the level of persecution. The IJ held that Ang does not have a well-founded fear of future persecution, given his multiple trips to and from Indonesia, and that death threats from Erlina's family do not give Erlina a well-founded fear of future persecution either. The IJ's ruling relied in part on the State Department's Country Conditions Report and International Religious Freedom Report, which indicate that Christians are not subject to a pattern or practice of persecution in Indonesia, and that the Indonesian government generally respects religious freedom.

On appeal, the BIA issued an order agreeing with the IJ's conclusions, although it implied that the IJ's decision was erroneous to the extent that it implied that Ang's religion or ethnicity was not a reason for his attack in the 1998 riot. The BIA concluded, however, that -this error would have been harmless because the attack did not constitute persecution. Finding no past persecution or well-founded fear of future persecution, the BIA dismissed the appeal. Ang and Erlina petitioned for review of the BIA's order.

II. Analysis

Because the BIA's decision affirmed the IJ's decision and added its own analysis, we review both. Cabas v. Hold er, 695 F.3d 169, 173 (1st Cir.2012). We review the BIA's and IJ's factual conclusions under the deferential "substantial evidence" standard, reversing only if a "reasonable adjudicator would be compelled to conclude to the contrary." Khan v. Mukasey, 549 F.3d 573, 576 (1st Cir.2008) (internal quotation marks omitted). Under this standard, we uphold the agency action so long as it is "supported by reasonable, substantial, and probative evidence on the record considered as a whole." Wu v. Holder, 705 F.3d 1, 3-4 (1st Cir.2013) (internal quotation marks omitted).

To establish eligibility for asylum, an alien must prove either past persecution, which gives rise to an inference of future persecution, or establish a well-founded fear of future persecution on account of his race, religion, nationality, membership in a social group, or political opinion. Sugiarto v. Holder, 586 F.3d 90, 94 (1st Cir.2009); see 8 U.S.C. §§ 1101(a)(42)(A), 1158(b)(l)(B)(i); 8 C.F.R. § 1208.13(b).

If an applicant establishes past persecution, there is a presumption of a well-founded fear of future persecution, and the burden shifts to the Government to rebut this presumption. 8 C.F.R. § 1208.13(b)(1); Sugiarto, 586 F.3d at 94. But even if the applicant cannot establish past persecution, he can nevertheless establish eligibility for asylum due to a well-founded fear of future persecution based on a protected ground. 8 C.F.R. § 1208.13(b). An applicant has a well-founded fear of persecution in his country if he can establish that his fear is both subjectively genuine and objectively reasonable, meaning that a reasonable person in the applicant's circumstances would fear *11 persecution. Sugiarto, 586 F.3d at 94; see 8 C.F.R. § 1208.13(b)(2). The regulations further provide that:

[i]n evaluating whether the applicant has sustained the burden of proving that he or she has a well-founded fear of persecution, the ... [IJ] shall not require the applicant to provide evidence that there is a reasonable possibility he or she would be singled out individually for persecution if ... [t]he applicant establishes that there is a pattern or practice in his or her country of nationality ... of persecution of a group of persons similarly situated to the applicant on account of race, religion, nationality, membership in a particular social group, or political opinion; and ... [t]he applicant establishes his or her own inclusion in, and identification with, such group of persons such that his or her fear of persecution upon return is reasonable.
8 C.F.R. § 1208.13(b)(2)(iii). 2
A. Past Persecution

"Establishing persecution requires evidence of experiences surpassing 'unpleasantness, harassment, and even basic suffering.' " Kho v. Keisler, 505 F.3d 50, 57 (1st Cir.2007) (quoting Nelson v. INS, 232 F.3d 258, 263 (1st Cir.2000)). One factor in determining whether persecution has occurred is the frequency of the alleged harm. Topalli v. Gonzales, 417 F.3d 128, 133 (1st Cir.2005); see also Decky v. Holder, 587 F.3d 104, 111 (1st Cir.2009) (holding that a beating suffered in the 1998 Indonesian riots was an "isolated" incident). Moreover, the applicant must show that the government participated in, or at least acquiesced in, the alleged harm. Decky, 587 F.3d at 110. To establish governmental acquiescence, "there must be some showing that the persecution is due to the government's unwillingness or inability to control the conduct of private actors." Jorgji v. Mukasey, 514 F.3d 53, 57 (1st Cir.2008).

Substantial evidence supported the BIA's and I J's conclusion that Ang did not establish past persecution. We acknowledge that Ang's stabbing must have been horrifying, and we will assume for the sake of argument that the beating of Ang's father was severe as well. But these two events occurred sixteen years apart, with Ang's stabbing occurring nine years before he sought asylum in the United States. These two incidents over the course of twenty-five years are too "isolated" to constitute persecution. See Decky, 587 F.3d at 111. 3 Moreover, substantial evidence supported the BIA's conclusion that "there was no government involvement [in the 1998 riots] to constitute persecution." Ang did not establish that during the 1998 riots, "police or other officials failed to protect him because of his ethnicity or religion." Kho, 505 F.3d at 58.

Erlina's beating by her family also does not constitute persecution. Again, while the beating itself must have been frightening and painful, it does not rise to the level of harm that amounts to persecution. And there was no evidence of government involvement or acquiescence in the beating by family members. Erlina's decision not to call the police based on her speculation that they would not protect her is not enough to show that the Indonesian government acquiesced in her mistreat *12 ment. See Barsoum v. Holder, 617 F.3d 73, 79 (1st Cir.2010) (decision not to report beating to police supported conclusion that the beating did not constitute persecution).

B. Well-Founded Fear of Future Persecution

Because they have not established past persecution, Ang and Erlina are eligible for asylum only if they can show that their fear of future persecution is both subjectively genuine and objectively reasonable.

The IJ and BIA concluded that Ang's fear of remaining in Indonesia was not subjectively genuine because he left Indonesia and returned three times before coming to the United States. See Pakasi v. Holder, 577 F.3d 44, 48 (1st Cir.2009) (departure from and return to Indonesia undermined petitioner's claim of fear of persecution). Nothing in the record compels a contrary conclusion.

The decisions of the IJ and BIA say little about Erlina's subjective fear of persecution, but even if we assume for the sake of argument that Erlina does have a genuine subjective fear of future persecution, that fear is not objectively reasonable. Erlina failed to establish that the Indonesian authorities cannot or will not protect her from her family. As to Ang and Erlina's more general allegations of the threat of future persecution, the IJ noted that "the [State Department's] Country Conditions Reports do not bear out that Christians are being subjected to a pattern or practice of persecution in Indonesia. The most recent International Religious Freedom Report indicates ... that the government generally respected religious freedom.... " The BIA cited these reports as well. "We have repeatedly affirmed the BIA's determinations ... that there is no ongoing pattern or practice of persecution against ethnic Chinese or Christians in Indonesia." Kho, 505 F.3d at 54. Ang and Erlina did file several articles and reports with the Immigration Court discussing the condition of ethnic Chinese and Christians in Indonesia, but the record as a whole does not compel a conclusion contrary to that of the BIA and IJ.

Because substantial evidence supports the IJ's and BIA's conclusion that Ang and Erlina lack a well-founded fear of future persecution, they cannot prove that they are eligible for asylum. For the same reason, they cannot meet the higher burden of proving eligibility for withholding of removal. Touch v. Holder, 568 F.3d 32, 41 (1st Cir.2009).

III. Conclusion

For the reasons given above, substantial evidence supported the conclusion of the IJ and the BIA that Ang and Erlina were not entitled to asylum. The petition for review is denied.""")

# Case 7
add_case("""De Carvalho Frois v. Holder
Court of Appeals for the First Circuit

Citations: 667 F.3d 69, 2012 WL 230023, 2012 U.S. App. LEXIS 1423
Docket Number: 11-1214
Judges: Boudin, Selya, Howard
Other Dates: Submitted Nov. 9, 2011.
Opinion
Authorities (7)
Cited By (13)
Summaries (2)
Similar Cases (3.2K)
PDF
Headmatter
Erika De CARVALHO-FROIS et al., Petitioners, v. Eric H. HOLDER, Jr., Attorney General, Respondent.

No. 11-1214.

United States Court of Appeals, First Circuit.

Submitted Nov. 9, 2011.
Decided Jan. 26, 2012.

*70 Carlos E. Estrada on brief for petitioner.

Tony West, Assistant Attorney General, Civil Division, Anthony W. Norwood, Senior Litigation Counsel, and Lisa Morinelli, Trial Attorney, Office of Immigration Litigation, on brief for respondent.

Before BOUDIN, SELYA and HOWARD, Circuit Judges.
Combined Opinion by Selya
SELYA, Circuit Judge.
The lead petitioner, Erika de Carvalho-Frois, is a Brazilian national. 1 She seeks judicial review of a final order of the Board of Immigration Appeals (BIA), which upheld a denial of asylum by an immigration judge (IJ). After careful consideration, we deny the petition for judicial review.

*71 The facts are not complicated. The petitioner entered the United States illegally on December 31, 2006. During her entry, she was apprehended by the Department of Homeland Security (DHS). About two months later, the DHS initiated removal proceedings on the ground that the petitioner had entered the United States without a valid entry document. See 8 U.S.C. § 1182(a)(7)(A)(i)(I). The petitioner conceded removability and cross-applied for asylum and other relief. 2

In her asylum application and in her testimony before the IJ, the petitioner related that she had repaired to the United States after witnessing two men fleeing from the scene of a neighbor's murder. Specifically, she said that on August 16, 2006, she heard gunshots while at home and saw two men leaving the neighbor's abode. As they left, one of them told her, "I know you saw everything. You're in danger. Be very careful." Later that evening, police officers found the neighbor's bullet-riddled body.

The petitioner took her son to her mother's house for the night. Upon returning home the next day, she received a telephone call, presumably from one of the assailants. The voice on the other end of the line said: "We know where, where you live. We know you. Please do not talk to the police about this, because if you do we will kill you." Following this conversation, the petitioner again retreated to her mother's house. She never returned home.

Approximately three weeks later, while the petitioner was bringing her son to school, she spotted the man who had threatened her on the night of the murder. She did not exchange words with him. Roughly four months after this encounter, she departed Brazil for the United States.

The petitioner testified that she never reported these incidents to the police because, in her view, the police in Brazil are corrupt and often allow criminals to kill witnesses. In an effort to support this supposition, she submitted various country-conditions reports, human rights reports, and a newspaper article. The petitioner further testified that she feared that she and her son would be killed either by the murderers or by the police should they return to Brazil. She admitted, however, that she had never been threatened by any police officer.

The IJ denied the petitioner's asylum application. She credited the petitioner's testimony regarding the threats, 3 but concluded that the petitioner had failed to establish either past persecution or a well-founded fear of future persecution.

The IJ deemed the evidence insufficient to show past persecution for three reasons. First, the threats were not serious enough to qualify as persecution. Second, the petitioner's fear was unconnected to any statutorily protected ground. Although she claimed "social group" membership, her *72 professed social group — witnesses to a serious crime whom the government is unable or unwilling to protect — was not legally cognizable. Third, the petitioner did not establish that the Brazilian government was either unable or unwilling to protect her from the harm that she feared.

The IJ likewise determined that the petitioner had no well-founded fear of future persecution. She mentioned some of the same reasons that she had recounted in rejecting the claim of past persecution. Additionally, the IJ determined that the petitioner's stated fear of returning to Brazil was objectively unreasonable because the petitioner had not established that the Brazilian authorities could not or would not protect her if she returned. In all events, the petitioner could relocate within Brazil to avoid being harmed by the purported murderers.

The petitioner unsuccessfully appealed the IJ's decision. The BIA concluded that the threats alleged by the petitioner did not constitute "mental, psychological, emotional [or] physical abuse amounting to persecution," that there was no nexus between the described threats and government action or inaction, and that the petitioner's claimed social group lacked social visibility (and, thus, was not legally cognizable). This timely petition for judicial review followed.

We review the factual findings underpinning the BIA's denial of an asylum application through the prism of the substantial evidence rubric. Morgan v. Holder, 634 F.3d 53, 56-57 (1st Cir.2011). Under that rubric, the agency's findings must be upheld so long as they are "supported by reasonable, substantial, and probative evidence on the record considered as a whole." INS v. Elias-Zacarias, 502 U.S. 478, 481, 112 S.Ct. 812, 117 L.Ed.2d 38 (1992). Absent an error of law, we will reject the agency's findings only when the record compels a conclusion contrary to that reached by the agency. Morgan, 634 F.3d at 57; Lopez Perez v. Holder, 587 F.3d 456, 460 (1st Cir.2009). Additionally, we review legal questions de novo, albeit with some deference to the BIA's reasonable interpretations of the statutes and regulations that fall within its purview. Mendez-Barrera v. Holder, 602 F.3d 21, 24 (1st Cir.2010).

To be eligible for asylum, an alien must show that "she is unable or unwilling to return to her homeland 'because of [past] persecution or a well-founded fear of [future] persecution on account of " one of five statutorily enumerated grounds. Id. at 25 (quoting 8 U.S.C. § 1101(a)(42)(A)) (alterations in original). "Persecution" is a term of art in immigration law. Lopez Perez, 587 F.3d at 461. The elements of persecution — past or future — are identical: the alien must demonstrate a certain level of serious harm (whether past or anticipated), a sufficient nexus between that harm and government action or inaction, and a causal connection to one of the statutorily protected grounds. Morgan, 634 F.3d at 57; Lopez Perez, 587 F.3d at 461-62.

If an alien establishes past persecution, a rebuttable presumption of a well-founded fear of future persecution arises. Mendez-Barrera, 602 F.3d at 25; Lopez Perez, 587 F.3d at 461. In the absence of proof of past persecution, an alien still can establish a well-founded fear of future persecution by demonstrating both that she genuinely fears future persecution and that her fears are objectively reasonable. Morgan, 634 F.3d at 57-58; Mendez-Barrera, 602 F.3d at 25.

In the case at hand, the petitioner complains that the BIA erred in affirming the IJ's determination that she failed to demonstrate either past persecution or a well-founded fear of future persecution. *73 We explain briefly why the petitioner's plaint fails.

An inability to establish any one of the three elements of persecution will result in a denial of her asylum application. See Morgan, 634 F.3d at 59; Lopez Perez, 587 F.3d at 462. Here, the IJ and the BIA found the petitioner's claims of persecution (both past and future) wanting in three fundamental respects. If the agency's findings on any one of those determinations are supportable, the petitioner cannot prevail. For simplicity's sake, then, we proceed directly to the weakest point in the petitioner's asseveratory array: the agency's determination that the petitioner's proposed social group was not cognizable.

To show persecution "on account of ... membership in a particular social group," 8 U.S.C. § 1101(a)(42)(A), an alien must establish that the putative social group is legally cognizable. Mendez-Barrera, 602 F.3d at 25. A cognizable social group is one whose members share "a common, immutable characteristic that makes the group socially visible and sufficiently particular." Id. For a group to be socially visible, "it must be generally recognized in the community as a cohesive group." Id. at 26; see Faye v. Holder, 580 F.3d 37, 41-42 (1st Cir.2009).

The petitioner asserts that her claimed social group — witnesses to a serious crime whom the Brazilian government, is unwilling or unable to protect — is socially visible. In this regard, she relies heavily on the fact that she had been identified by the murderers. Building on this foundation, she speculates that the murderers' entire gang (which assumes without a shred of proof that the murderers belonged to a gang) and complicit Brazilian police officers knew that she had witnessed the two men flee the murder scene. Because her status as a witness to a serious crime was known to those seeking to do her harm, her thesis runs, her claimed social group was socially visible.

This line of argument mistakes the proper inquiry. In determining whether a purported social group is socially visible, the relevant question is "whether the social group is visible in the society, not whether the alien herself is visible to the alleged persecutors." Mendez-Barrera, 602 F.3d at 27. The fact that the petitioner was known by a select few to have witnessed a crime tells us nothing about whether the putative social group was recognizable to any extent by the community. Cf. Scatambuli v. Holder, 558 F.3d 53, 60 (1st Cir.2009) (commenting, in the course of upholding a finding that a claimed social group lacked social visibility, that "the universe of those who knew of the petitioners' identity as informants was quite small [and] the petitioners were not particularly visible.").

Here, moreover, the visibility of the putative social group is deficient in yet another respect; the petitioner has pointed to no common and immutable characteristic that renders members of the group socially visible in Brazil. This, in itself, is a fatal flaw. See Mendez-Barrera, 602 F.3d at 26-27. Because we discern no feature of the group that would enable the community readily to differentiate witnesses to a serious crime from the Brazilian populace as a whole, the claimed group is simply too amorphous to satisfy the requirements for social visibility. See id.

Our holding today is consistent with the case law in this circuit: the claimed social group of witnesses to a serious crime whom the government is unable or unwilling to protect is not appreciably more visible than other proposed groups previously found not to be cognizable. See, e.g., id. (upholding agency's determination that the *74 proposed group of "young women recruited by gang members who resist such recruitment" is not socially visible); Faye, 580 F.3d at 41-42 (upholding agency's determination that proposed group of women who had a child out of wedlock is not socially visible); Scatambuli, 558 F.3d at 60-61 (upholding agency's determination that proposed group of informants is not socially visible). We therefore conclude that the BIA did not err in finding that the petitioner's professed social group was not legally cognizable.

This gap in the petitioner's proof dooms her claims of past persecution and a well-founded fear of future persecution alike. Each formulation requires that the persecution be perpetrated "on account of' one of the statutorily enumerated grounds. 8 U.S.C. § 1101(a)(42)(A). The petitioner chose to premise both her claim of. past persecution and her claim of well-founded fear of future persecution on her membership in a group that lacks the requisite social visibility. Consequently, both claims topple.

We need go no further. 4 The petitioner's failure to satisfy an essential element of the three-part showing needed to ground a finding of persecution requires us to deny her petition for judicial review.

The petition for judicial review is denied.""")

# Case 8
add_case("""Immigration & Naturalization Service v. Cardoza-Fonseca
Supreme Court of the United States

Citations: 480 U.S. 421, 107 S. Ct. 1207, 94 L. Ed. 2d 434, 55 U.S.L.W. 4313, 1987 U.S. LEXIS 1059
Docket Number: 85-782
Judges: Stevens, Brennan, Marshall, Blackmun, O'Connor, Scalia, Powell, Rehnquist, White
Other Dates: Argued October 7, 1986
Opinion
Authorities (55)
Cited By (3.3K)
Summaries (580)
Similar Cases (1.7K)
PDF
Headmatter
IMMIGRATION AND NATURALIZATION SERVICE v. CARDOZA-FONSECA

No. 85-782.
Argued October 7, 1986
Decided March 9, 1987

*422 Stevens, J., delivered the opinion of the Court, in which Brennan, Marshall, Blackmun, and O'Connor, JJ., joined. Blackmun, J., filed a concurring opinion, post, p. 450. Scalia, J., filed an opinion concurring in the judgment, post, p. 452. Powell, J., filed a dissenting opinion, in which Rehnquist, C. J., and White, J., joined, post, p. 455.
Deputy Solicitor General Wallace argued the cause for petitioner. With him on the briefs were Solicitor General Fried, Assistant Attorney General Willard, Deputy Solicitor General Kuhl, Bruce N. Kuhlik, and David V. Bernal.

Dana Marks Keener argued the cause for respondent. With her on the brief was Bill Ong Hing. *
 * Briefs of amici curiae urging affirmance were filed for the United Nations High Commissioner for Refugees by Ralph G. Steinhardt; for the American Civil Liberties Union et al. by Carol Leslie Wolchok, Burt Neuborne, Lucas Guttentag, Jack Novik, and Robert N. Weiner; for the American Immigration Lawyers Association by Ira J. Kurzban; for the International Human Rights Law Group et al. by E. Edward Bruce; and for the Lawyers Committee for Human Rights et al. by Richard F. Ziegler, Arthur C. Helton, Samuel Rabinove, Richard T. Foltin, Ruti G. Teitel, Steven M. Freeman, and Richard J. Rubin. ↵
Lead Opinion by Stevens
*423Justice Stevens delivered the opinion of the Court.
Since 1980, the Immigration and Nationality Act has provided two methods through which an otherwise deportable alien who claims that he will be persecuted if deported can seek relief. Section 243(h) of the Act, 8 U. S. C. § 1253(h), requires the Attorney General to withhold deportation of an alien who demonstrates that his "life or freedom would be threatened" on account of one of the listed factors if he is deported. In INS v. Stevic, 467 U. S. 407 (1984), we held that to qualify for this entitlement to withholding of deportation, an alien must demonstrate that "it is more likely than not that the alien would be subject to persecution" in the country to which he would be returned. Id., at 429-430. The Refugee Act of 1980, 94 Stat. 102, also established a second type of broader relief. Section 208(a) of the Act, 8 U. S. C. § 1158(a), authorizes the Attorney General, in his discretion, to grant asylum to an alien who is unable or unwilling to return to his home country "because of persecution or a well-founded fear of persecution on account of race, religion, nationality, membership in a particular social group, or political opinion." § 101(a)(42), 8 U. S. C. § 1101(a)(42).

In Stevie, we rejected an alien's contention that the § 208(a) "well-founded fear" standard governs applications for withholding of deportation under 1243(h).1 Similarly, today we reject the Government's contention that the § 243(h) standard, which requires an alien to show that he is more likely than not to be subject to persecution, governs applications for asylum under § 208(a). Congress used different, broader language to define the term "refugee" as used in § 208(a) than it used to describe the class of aliens who have *424a right to withholding of deportation under § 243(h). The Act's establishment of a broad class of refugees who are eligible for a discretionary grant of asylum, and a narrower class of aliens who are given a statutory right not to be deported to the country where they are in danger, mirrors the provisions of the United Nations Protocol Relating to the Status of Refugees, which provided the motivation for the enactment of the Refugee Act of 1980. In addition, the legislative history of the 1980 Act makes it perfectly clear that Congress did not intend the class of aliens who qualify as refugees to be coextensive with the class who qualify for § 243(h) relief.

I

Respondent is a 38-year-old Nicaraguan citizen who entered the United States in 1979 as a visitor. After she remained in the United States longer than permitted, and failed to take advantage of the Immigration and Naturalization Service's (INS) offer of voluntary departure, the INS commenced deportation proceedings against her. Respondent conceded that she was in the country illegally, but requested withholding of deportation pursuant to § 243(h) and asylum as a refugee pursuant to § 208(a).

To support her request under § 243(h), respondent attempted to show that if she were returned to Nicaragua her "life or freedom would be threatened" on account of her political views; to support her request under § 208(a), she attempted to show that she had a "well-founded fear of persecution" upon her return. The evidence supporting both claims related primarily to the activities of respondent's brother who had been tortured and imprisoned because of his political activities in Nicaragua. Both respondent and her brother testified that they believed the Sandinistas knew that the two of them had fled Nicaragua together and that even though she had not been active politically herself, she would be interrogated about her brother's whereabouts and *425activities. Respondent also testified that because of her brother's status, her own political opposition to the Sandinis-tas would be brought to that government's attention. Based on these facts, respondent claimed that she would be tortured if forced to return.

The Immigration Judge applied the same standard in evaluating respondent's claim for withholding of deportation under § 248(h) as he did in evaluating her application for asylum under § 208(a). He found that she had not established "a clear probability of persecution" and therefore was not entitled to either form of relief. App. to Pet. for Cert. 27a. On appeal, the Board of Immigration Appeals (BIA) agreed that respondent had "failed to establish that she would suffer persecution within the meaning of section 208(a) or 243(h) of the Immigration and Nationality Act." Id., at 21a.

In the Court of Appeals for the Ninth Circuit, respondent did not challenge the BIA's decision that she was not entitled to withholding of deportation under § 243(h), but argued that she was eligible for consideration for asylum under § 208(a), and contended that the Immigration Judge and BIA erred in applying the "more likely than not" standard of proof from § 243(h) to her § 208(a) asylum claim. Instead, she asserted, they should have applied the "well-founded fear" standard, which she considered to be more generous. The court agreed. Relying on both the text and the structure of the Act, the court held that the "well-founded fear" standard which governs asylum proceedings is different, and in fact more generous, than the "clear probability" standard which governs withholding of deportation proceedings. 767 F. 2d 1448, 1452-1453 (1985). Agreeing with the Court of Appeals for the Seventh Circuit, the court interpreted the standard to require asylum applicants to present " 'specific facts' through objective evidence to prove either past persecution or 'good reason' to fear future persecution." Id., at 1453 (citing Carvajal-Munoz v. INS, 743 F. 2d 562, 574 (CA7 1984)). *426The court remanded respondent's asylum claim to the BIA to evaluate under the proper legal standard. We granted cer-tiorari to resolve a Circuit conflict on this important question.2 475 U. S. 1009 (1986).3

*427I — I HH

The Refugee Act of 1980 established a new statutory procedure for granting asylum to refugees.4 The 1980 Act added a new § 208(a) to the Immigration and Nationality Act of 1952, reading as follows:

"The Attorney General shall establish a procedure for an alien physically present in the United States or at a land border or port of entry, irrespective of such alien's status, to apply for asylum, and the alien may be granted asylum in the discretion of the Attorney General if the Attorney General determines that such alien is a refugee within the meaning of section 1101(a)(42)(A) of this title." 94 Stat. 105, 8 U. S. C. § 1158(a).
Under this section, eligibility for asylum depends entirely on the Attorney General's determination that an alien is a *428"refugee," as that term is defined in § 101(a)(42), which was also added to the Act in 1980. That section provides:

"The term 'refugee' means (A) any person who is outside any country of such person's nationality or, in the case of a person having no nationality, is outside any country in which such person last habitually resided, and who is unable or unwilling to return to, and is unable or unwilling to avail himself or herself of the protection of, that country because of persecution or a well-founded fear of persecution on account of race, religion, nationality, membership in a particular social group, or political opinion . . . 94 Stat. 102, 8 U. S. C. § 1101(a)(42).
Thus, the "persecution or well-founded fear of persecution" standard governs the Attorney General's determination whether an alien is eligible for asylum.5

In addition to establishing a statutory asylum process, the 1980 Act amended the withholding of deportation provision,6 *429§ 243(h). See Stevic, 467 U. S., at 421, n. 16. Prior to 1968, the Attorney General had discretion whether to grant withholding of deportation to aliens under § 243(h). In 1968, however, the United States agreed to comply with the substantive provisions of Articles 2 through 34 of the 1951 United Nations Convention Relating to the Status of Refugees. See 19 U.S.T. 6223, 6259-6276, T.I.A.S. No. 6577 (1968); see generally Stevie, supra, at 416-417. Article 33.1 of the Convention, 189 U.N.T.S. 150, 176 (1954), reprinted in 19 U.S.T. 6259, 6276, which is the counterpart of §243(h) of our statute, imposed a mandatory duty on contracting States not to return an alien to a country where his "life or freedom would be threatened" on account of one of the enumerated reasons.7 See infra, at 441. Thus, although § 243(h) itself did not constrain the Attorney General's discretion after 1968, presumably he honored the dictates of the United Nations Convention.8 In any event, the 1980 Act removed the Attorney General's discretion in § 243(h) proceedings.9

*430In Stevie we considered it significant that in enacting the 1980 Act Congress did not amend the standard of eligibility for relief under § 243(h). While the terms "refugee" and hence "well-founded fear" were made an integral part of the § 208(a) procedure, they continued to play no part in § 243(h). Thus we held that the prior consistent construction of § 243(h) that required an applicant for withholding of deportation to demonstrate a "clear probability of persecution" upon deportation remained in force. Of course, this reasoning, based in large part on the plain language of § 243(h), is of no avail here since § 208(a) expressly provides that the "well-founded fear" standard governs eligibility for asylum.

The Government argues, however, that even though the "well-founded fear" standard is applicable, there is no difference between it and the "would be threatened" test of § 243(h). It asks us to hold that the only way an applicant can demonstrate a "well-founded fear of persecution" is to prove a "clear probability of persecution." The statutory language does not lend itself to this reading.

To begin with, the language Congress used to describe the two standards conveys very different meanings. The "would be threatened" language of § 243(h) has no subjective component, but instead requires the alien to establish by objective evidence that it is more likely than not that he or she will be subject to persecution upon deportation.10 See Stevie, supra. In contrast, the reference to "fear" in the § 208(a) standard obviously makes the eligibility determination turn to some extent on the subjective mental state of the *431lien.11 "The linguistic difference between the words 'well-ounded fear' and 'clear probability' may be as striking as that jetween a subjective and an objective frame of reference.

. . We simply cannot conclude that the standards are identi:al." Guevara-Flores v. INS, 786 F. 2d 1242, 1250 (CA5 1986), cert. pending, No. 86-388; see also Carcamo-Flores v. INS, 805 F. 2d 60, 64 (CA2 1986); 767 F. 2d, at 1452 (case below).

That the fear must be "well-founded" does not alter the obvious focus on the individual's subjective beliefs, nor does it transform the standard into a "more likely than not" one. One can certainly have a well-founded fear of an event happening when there is less than a 50% chance of the occurrence taking place. As one leading authority has pointed out:

"Let us . . . presume that it is known that in the applicant's country of origin every tenth adult male person is either put to death or sent to some remote labor camp. ... In such a case it would be only too apparent that anyone who has managed to escape from the country in question will have 'well-founded fear of being persecuted' upon his eventual return." 1 A. Grahl-Madsen, The Status of Refugees in International Law 180 (1966).
This ordinary and obvious meaning of the phrase is not to be lightly discounted. See Russello v. United States, 464 U. S. 16, 21 (1983); Ernst & Ernst v. Hochfelder, 425 U. S. 185, 198-199 (1976). With regard to this very statutory scheme, we have considered ourselves bound to " 'assume "that .the legislative purpose is expressed by the ordinary meaning of the words used."'" INS v. Phinpathya, 464 U. S. 183, 189 (1984) (quoting American Tobacco Co. v. Patterson, 456 *432U. S. 63, 68 (1982), in turn quoting Richards v. United States, 369 U. S. 1, 9 (1962)).

The different emphasis of the two standards which is so clear on the face of the statute is significantly highlighted by the fact that the same Congress simultaneously drafted § 208(a) and amended § 243(h). In doing so, Congress chose to maintain the old standard in § 243(h), but to incorporate a different standard in § 208(a). " '[W]here Congress includes particular language in one section of a statute but omits it in another section of the same Act, it is generally presumed that Congress acts intentionally and purposely in the disparate inclusion or exclusion.'" Russello v. United States, supra, at 23 (quoting United States v. Wong Kim Bo, 472 F. 2d 720, 722 (CA5 1972)). The contrast between the language used in the two standards, and the fact that Congress used a new standard to define the term "refugee," certainly indicate that Congress intended the two standards to differ.

I — l I — I

The message conveyed by the plain language of the Act is confirmed by an examination of its history.12 Three aspects of that history are particularly compelling: The pre-1980 experience under § 203(a)(7), the only prior statute dealing with asylum; the abundant evidence of an intent to conform the definition of "refugee" and our asylum law to the United Nations Protocol to which the United States has been bound *433since 1968; and the fact that Congress declined to enact the Senate version of the bill that would have made a refugee ineligible for asylum unless "his deportation or return would be prohibited by § 243(h)."

The Practice Under § 203(a)(7).

The statutory definition of the term "refugee" contained in § 101(a)(42) applies to two asylum provisions within the Immigration and Nationality Act.13 Section 207, 8 U. S. C. § 1157, governs the admission of refugees who seek admission from foreign countries. Section 208, 8 U. S. C. § 1158, sets out the process by which refugees currently in the United States may be granted asylum. Prior to the 1980 amendments there was no statutory basis for granting asylum to aliens who applied from within the United States.14 Asylum for aliens applying for admission from foreign countries had, however, been the subject of a previous statutory provision, and Congress' intent with respect to the changes that it sought to create in that statute are instructive in discerning the meaning of the term "well-founded fear."

Section § 203(a)(7) of the pre-1980 statute authorized the Attorney General to permit "conditional entry" to a certain number of refugees fleeing from Communist-dominated areas or the Middle East "because of persecution or fear of persecution on account of race, religion, or political opinion." 79 *434Stat. 913, 8 U. S. C. § 1153(a)(7) (1976 ed.). The standard that was applied to aliens seeking admission pursuant to § 203(a)(7) was unquestionably more lenient than the "clear probability" standard applied in § 243(h) proceedings. In Matter of Tan, 12 I. & N. Dec. 564, 569-570 (1967), for example, the BIA "found no support" for the argument that "an alien deportee is required to do no more than meet the standards applied under section 203(a)(7) of the Act when seeking relief under section 243(h)." Similarly, in Matter of Adamska, 12 I. & N. Dec. 201, 202 (1967), the Board held that an alien's inability to satisfy § 243(h) was not determinative of her eligibility under the "substantially broader" standards of § 203(a)(7). One of the differences the Board highlighted between the statutes was that § 243(h) requires a showing that the applicant "would be" subject to persecution, while § 203(a)(7) only required a showing that the applicant was unwilling to return "because of persecution or fear of persecution." 12 I. & N., at 202 (emphasis in original). In sum, it was repeatedly recognized that the standards were significantly different.15

At first glance one might conclude that this wide practice under the old § 203(a)(7), which spoke of "fear of persecution," is not probative of the meaning of the term "well-founded fear of persecution" which Congress adopted in 1980. Analysis of the legislative history, however, demonstrates that Congress added the "well-founded" language only because that was the language incorporated by the United Nations Protocol to which Congress sought to conform. See infra, at 436-437. Congress was told that the extant asylum proce*435dure for refugees outside of the United States was acceptable under the Protocol, except for the fact that it made various unacceptable geographic and political distinctions.16 The legislative history indicates that Congress in no way wished to modify the standard that had been used under § 203(a)(7).17 *436Adoption of the INS's argument that the term "well-founded fear" requires a showing of clear probability of persecution would clearly do violence to Congress' intent that the standard for admission under §207 be no different than the one previously applied under § 203(a)(7).18

The United Nations Protocol.

If one thing is clear from the legislative history of the new definition of "refugee," and indeed the entire 1980 Act, it is that one of Congress' primary purposes was to bring United States refugee law into conformance with the 1967 United Nations Protocol Relating to the Status of Refugees, 19 U.S.T. 6223, T.I.A.S. No. 6577, to which the United States *437acceded in 1968.19 Indeed, the definition of "refugee" that Congress adopted, see supra, at 428, is virtually identical to the one prescribed by Article 1(2) of the Convention which defines a "refugee" as an individual who

"owing to a well-founded fear of being persecuted for reasons of race, religion, nationality, membership of a particular social group or political opinion, is outside the country of his nationality and is unable or, owing to such fear, is unwilling to avail himself of the protection of that country; or who, not having a nationality and being outside the country of his former habitual residence, is unable or, owing to such fear, is unwilling to return to it."
Compare 19 U.S.T. 6225 with 19 U.S.T. 6261. Not only did Congress adopt the Protocol's standard in the statute, but there were also many statements indicating Congress' intent that the new statutory definition of "refugee" be interpreted in conformance with the Protocol's definition. The Conference Committee Report, for example, stated that the definition was accepted "with the understanding that it is based directly upon the language of the Protocol and it is intended that the provision be construed consistent with the Protocol." S. Rep. No. 96-590, p. 20 (1980); see also H. R. Rep., at 9. It is thus appropriate to consider what the phrase "well-founded fear" means with relation to the Protocol.

The origin of the Protocol's definition of "refugee" is found in the 1946 Constitution of the International Refugee Organization (IRO). See 62 Stat. 3037. The IRO defined a "refugee" as a person who had a "valid objection" to returning to his country of nationality, and specified that "fear, based on reasonable grounds of persecution because of race, religion, nationality, or political opinions ..." constituted a valid objection. See IRO Constitution, Annex 1, Pt. 1, § Cl(a)(i). The term was then incorporated in the United Nations Con*438vention Relating to the Status of Refugees,20 189 U.N.T.S. 150 (July 28, 1951). The Committee that drafted the provision explained that "[t]he expression 'well-founded fear of being the victim of persecution . . .' means that a person has either been actually a victim of persecution or can show good reason why he fears persecution." U. N. Rep., at 39. The 1967 Protocol incorporated the "well-founded fear" test, without modification. The standard, as it has been consistently understood by those who drafted it, as well as those drafting the documents that adopted it, certainly does not require an alien to show that it is more likely than not that he will be persecuted in order to be classified as a "refugee."21

In interpreting the Protocol's definition of "refugee" we are further guided by the analysis set forth in the Office of the *439United Nations High Commissioner for Refugees, Handbook on Procedures and Criteria for Determining Refugee Status (Geneva, 1979).22 The Handbook explains that "[i]n general, the applicant's fear should be considered well founded if he can establish, to a reasonable degree, that his continued stay-in his country of origin has become intolerable to him for the reasons stated in the definition, or would for the same reasons be intolerable if he returned there." Id., at Ch. II B(2)(a) §42; see also id., §§37-41.

The High Commissioner's analysis of the United Nations' standard is consistent with our own examination of the origins of the Protocol's definition,23 as well as the conclusions of *440many scholars who have studied the matter.24 There is simply no room in the United Nations' definition for concluding that because an applicant only has a 10% chance of being shot, tortured, or otherwise persecuted, that he or she has no "well-founded fear" of the event happening. See supra, at 431. As we pointed out in Stevic, a moderate interpretation of the "well-founded fear" standard would indicate "that so long as an objective situation is established by the evidence, it need not be shown that the situation will probably result in persecution, but it is enough that persecution is a reasonable possibility." 467 U. S., at 424-425.

In Stevic, we dealt with the issue of withholding of deportation, or nonrefoulement, under § 243(h). This provision corresponds to Article 33.1 of the Convention.25 Significantly though, Article 33.1 does not extend this right to everyone who meets the definition of "refugee." Rather, it provides that "[n]o Contracting State shall expel or return ('refouler') a refugee in any manner whatsoever to the frontiers or territories where his life or freedom would be threatened on account of his race, religion, nationality, membership or a particular social group or political opinion." 19 U.S.T., at 6276,189 U.N.T.S., at 176 (emphasis added). Thus, Article 33.1 requires that an applicant satisfy two burdens: first, that he or she be a "refugee," i. e., prove at least a "well-*441founded fear of persecution"; second, that the "refugee" show that his or her life or freedom "would be threatened" if deported. Section 243(h)'s imposition of a "would be threatened" requirement is entirely consistent with the United States' obligations under the Protocol.

Section 208(a), by contrast, is a discretionary mechanism which gives the Attorney General the authority to grant the broader relief of asylum to refugees. As such, it does not correspond to Article 33 of the Convention, but instead corresponds to Article 34. See Carvajal-Munoz, 743 F. 2d, at 574, n. 15. That Article provides that the contracting States "shall as far as possible facilitate the assimilation and naturalization of refugees. ..." Like § 208(a), the provision is prec-atory; it does not require the implementing authority actually to grant asylum to all those who are eligible. Also like § 208(a), an alien must only show that he or she is a "refugee" to establish eligibility for relief. No further showing that he or she "would be" persecuted is required.

Thus, as made binding on the United States through the Protocol, Article 34 provides for a precatory, or discretionary, benefit for the entire class of persons who qualify as "refugees," whereas Article 33.1 provides an entitlement for the subcategory that "would be threatened" with persecution upon their return. This precise distinction between the broad class of refugees and the subcategory entitled to § 243(h) relief is plainly revealed in the 1980 Act. See Stevic, 467 U. S., at 428, n. 22.

Congress' Rejection of S. 64.3.

Both the House bill, H. R. 2816, 96th Cong., 1st Sess. (1979), and the Senate bill, S. 643, 96th Cong., 1st Sess. (1979), provided that an alien must be a "refugee" within the meaning of the Act in order to be eligible for asylum. The two bills differed, however, in that the House bill authorized the Attorney General, in his discretion, to grant asylum to any refugee, whereas the Senate bill imposed the additional *442requirement that a refugee could not obtain asylum unless "his deportation or return would be prohibited under section 243(h)."26 S. Rep., at 26. Although this restriction, if adopted, would have curtailed the Attorney General's discretion to grant asylum to refugees pursuant to § 208(a), it would not have affected the standard used to determine whether an alien is a "refugee." Thus, the inclusion of this prohibition in the Senate bill indicates that the Senate recognized that there is a difference between the "well-founded fear" standard and the clear-probability standard.27 The enactment of the House bill rather than the Senate bill in turn demonstrates that Congress eventually refused to restrict eligibility for asylum only to aliens meeting the stricter standard. "Few principles of statutory construction are more compelling than the proposition that Congress does not intend sub *443silentio to enact statutory language that it has earlier discarded in favor of other language." Nachman Corp. v. Pension Benefit Guaranty Corporation, 446 U. S. 359, 392-393 (1980) (Stewart, J., dissenting); cf. Gulf Oil Corp. v. Copp Paving Co., 419 U. S. 186, 200 (1974); Russello v. United States, 464 U. S., at 23.

IV

The INS makes two major arguments to support its contention that we should reverse the Court of Appeals and hold that an applicant can only show a "well-founded fear of persecution" by proving that it is more likely than not that he or she will be persecuted. We reject both of these arguments: the first ignores the structure of the Act; the second misconstrues the federal courts' role in reviewing an agency's statutory construction.

First, the INS repeatedly argues that the structure of the Act dictates a decision in its favor, since it is anomalous for § 208(a), which affords greater benefits than § 243(h), see n. 6, supra, to have a less stringent standard of eligibility. This argument sorely fails because it does not take into account the fact that an alien who satisfies the applicable standard under § 208(a) does not have a right to remain in the United States; he or she is simply eligible for asylum, if the Attorney General, in his discretion, chooses to grant it. An alien satisfying §243(h)'s stricter standard, in contrast, is automatically entitled to withholding of deportation.28 In Matter of Salim, 18 I. & N. Dec. 311 (1982), for example, the Board held that the alien was eligible for both asylum and withholding of deportation, but granted him the more limited remedy only, exercising its discretion to deny him asylum. See also Walai v. INS, 552 F. Supp. 998 (SDNY 1982); Mat*444ter of Shirdel, Interim Decision No. 2958 (BIA Feb. 21, 1984). We do not consider it at all anomalous that out of the entire class of "refugees," those who can show a clear probability of persecution are entitled to mandatory suspension of deportation and eligible for discretionary asylum, while those who can only show a well-founded fear of persecution are not entitled to anything, but are eligible for the discretionary relief of asylum.

There is no basis for the INS's assertion that the discretionary/mandatory distinction has no practical significance. Decisions such as Matter of Salim, supra, and Matter of Shirdel, swpra, clearly demonstrate the practical import of the distinction. Moreover, the 1980 Act amended § 243(h) for the very purpose of changing it from a discretionary to a mandatory provision. See supra, at 428-429. Congress surely considered the discretionary/mandatory distinction important then, as it did with respect to the very definition of "refugee" involved here. The House Report provides:

"The Committee carefully considered arguments that the new definition might expand the numbers of refugees eligible to come to the United States and force substantially greater refugee admissions than the country could absorb. However, merely because an individual or group comes within the definition will not guarantee resettlement in the United States." H. R. Rep., at 10.
This vesting of discretion in the Attorney General is quite typical in the immigration area, see, e. g., INS v. Jong Ha Wang, 450 U. S. 139 (1981). If anything is anomalous, it is that the Government now asks us to restrict its discretion to a narrow class of aliens. Congress has assigned to the Attorney General and his delegates the task of making these hard individualized decisions; although Congress could have crafted a narrower definition, it chose to authorize the At*445torney General to determine which, if any, eligible refugees should be denied asylum.

The INS's second principal argument in support of the proposition that the "well-founded fear" and "clear probability" standard are equivalent is that the BIA so construes the two standards. The INS argues that the BIA's construction of the Refugee Act of 1980 is entitled to substantial deference, even if we conclude that the Court of Appeals' reading of the statutes is more in keeping with Congress' intent.29 This argument is unpersuasive.

*446The question whether Congress intended the two standards to be identical is a pure question of statutory construction for the courts to decide. Employing traditional tools of statutory construction, we have concluded that Congress did not intend the two standards to be identical.30 In Chevron *447U. S. A. Inc. v. Natural Resources Defense Council, Inc., 467 U. S. 837 (1984), we explained:

"The judiciary is the final authority-on issues of statutory construction and must reject administrative constructions which are contrary to clear congressional *448intent. [Citing cases.] If a court, employing traditional tools of statutory construction, ascertains that Congress had an intention on the precise question at issue, that intention is the law and must be given effect." Id., at 843, n. 9 (citations omitted).
The narrow legal question whether the two standards are the same is, of course, quite different from the question of interpretation that arises in each case in which the agency is required to apply either or both standards to a particular set of facts. There is obviously some ambiguity in a term like "well-founded fear" which can only be given concrete meaning through a process of case-by-case adjudication. In that process of filling "'any gap left, implicitly or explicitly, by Congress,'" the courts must respect the interpretation of the agency to which Congress has delegated the responsibility for administering the statutory program. See Chevron, supra, at 843, quoting Morton v. Ruiz, 415 U. S. 199, 231 (1974). But our task today is much narrower, and is well within the province of the Judiciary. We do not attempt to set forth a detailed description of how the "well-founded fear" test should be applied.31 Instead, we merely hold that the Immigration Judge and the BIA were incorrect in holding that the two standards are identical.32

*449Our analysis of the plain language of the Act, its symmetry with the United Nations Protocol, and its legislative history, lead inexorably to the conclusion that to show a "well-founded fear of persecution," an alien need not prove that it is more likely than not that he or she will be persecuted in his or her home country. We find these ordinary canons of statutory construction compelling, even without regard to the longstanding principle of construing any lingering ambiguities in deportation statutes in favor of the alien. See INS v. Errico, 385 U. S. 214, 225 (1966); Costello v. INS, 376 U. S. 120, 128 (1964); Fong Haw Tan v. Phelan, 333 U. S. 6, 10 (1948).

Deportation is always a harsh measure; it is all the more replete with danger when the alien makes a claim that he or she will be subject to death or persecution if forced to return to his or her home country. In enacting the Refugee Act of 1980 Congress sought to "give the United States sufficient flexibility to respond to situations involving political or religious dissidents and detainees throughout the world." H. R. Rep., at 9. Our holding today increases that flexibility by rejecting the Government's contention that the Attorney General may not even consider granting asylum to one who *450fails to satisfy the strict § 243(h) standard. Whether or not a "refugee" is eventually granted asylum is a matter which Congress has left for the Attorney General to decide. But it is clear that Congress did not intend to restrict eligibility for that relief to those who could prove that it is more likely than not that they will be persecuted if deported.

The judgment of the Court of Appeals is

Affirmed.""")

# Case 9
add_case("""United States v. Ilario M.A. Zannino
Court of Appeals for the First Circuit

Citations: 895 F.2d 1, 106 A.L.R. Fed. 1, 29 Fed. R. Serv. 838, 1990 WL 965, 1990 U.S. App. LEXIS 336
Docket Number: 87-1221
Judges: Bownes, Breyer, Selya
Other Dates: Heard Nov. 7, 1989.
Opinion
Authorities (83)
Cited By (2.4K)
Summaries (635)
Similar Cases (248)
PDF
Headmatter
UNITED STATES of America, Appellee, v. Ilario M.A. ZANNINO, Defendant, Appellant.

No. 87-1221.

United States Court of Appeals, First Circuit.

Heard Nov. 7, 1989.
Decided Jan. 10, 1990.

*3 Joseph J. Balliro, with whom Edward J. Romano was on brief for defendant, appellant.

Frank J. Marine, A.tty., Dept, of Justice, with whom Ernest Dinisco, Sp. Atty., Dept, of Justice, and Wayne A. Budd, U.S. Atty., were on brief for the United States.

Before BOWNES, BREYER and SELYA, Circuit Judges.
Combined Opinion by Selya
SELYA, Circuit Judge.
In 1983, defendant-appellant Ilario M.A. Zannino, allegedly a predominant figure in the so-called "Patriarca Family" of La Cosa Nostra, was indicted by a federal grand jury. The indictment charged Zannino and several codefendants with conspiring to participate in an enterprise through a pattern of racketeering activity in violation of 18 U.S.C. § 1962(c), (d), and with a number of racketeering, loansharking, and gambling violations. The listed predicate acts included two murders and four conspiracies to commit murder. Zannino stood trial after the others, 1 and then, on only three of the original eight counts directed against him. Having been found guilty before a jury and sentenced to a 30-year prison term, he prosecutes this appeal. We affirm.

I. BACKGROUND

Zannino's indictment grew out of the judicially sanctioned electronic surveillance of apartments at 98 Prince Street and 51 North Margin Street in Boston's North *4 End. 2 Hidden microphones recorded numerous conversations among various persons, including Zannino and his codefend-ants, during the period January-May 1981. The FBI monitored the conversations and, in addition, photographed persons entering and leaving the premises. We summarize certain critical data, taking the evidence as the jury could permissibly have found it, viewing the record in the light most congenial to the prosecution, and drawing all reasonable inferences in the government's favor. See United States v. Ingraham, 832 F.2d 229, 230 (1st Cir.1987), cert. denied, 486 U.S. 1009, 108 S.Ct. 1738, 100 L.Ed.2d 202 (1988); United States v. Cintolo, 818 F.2d 980, 983 (1st Cir.), cert. denied, 484 U.S. 913, 108 S.Ct. 259, 98 L.Ed.2d 216 (1987).

The evidence indicated that the surveilled premises were used as the headquarters for the operation of prosperous, but illegal, gambling and loansharking businesses. Gennaro Angiulo was at the apex of the criminal pyramid and, as such, was ultimately responsible for the delegation of tasks to others. 3 Zannino was a "Capo Regime" — loosely, a captain — in the Patr-iarca Family, serving under Angiulo.

From at least the fall of 1980 to late spring of 1981, high stakes poker games were held at North Margin St. Photographic surveillance of the building's outside entrance revealed a regular flow of players coming and going. Intercepted conversations disclosed that the poker games were "owned" by a quinquevirate comprised of Zannino, Angiulo, Granito, Ralph Lamattina, and Nick Giso. Frances-co Angiulo served as the operation's accountant. John Cincotti managed the staff, collected the dealers' tips, arranged credit for the gamblers, and collected debts. Zannino was the chief operating officer of the venture, supervising Cincotti, determining player eligibility, and overseeing the debt collection function. Donald Smoot was a poker player to whom the house frequently extended credit.

Zannino was also deeply involved with Angiulo in a loansharking operation. 4 They were often overheard discussing aspects of the business. Among other things, the loansharks furnished venture capital to gamblers. By early 1981, Smoot owed Zannino $14,000. Smoot made interest payments on this debt at the rate of one percent per week ($140), paying the money to Zannino, Cincotti, or Donato Angiulo. When Zannino "assigned" $2,000 of the principal to Dominic Isabella, Smoot began to make hebdomadal interest payments to Isabella at twice the rate. Smoot was well aware that, considering the circumstances, he could be threatened with physical harm or violence if he failed to pay his indebtedness to appellant.

The evidence at trial also implicated Zan-nino in a barbooth gambling business 5 at the Demosthenes Democratic Social Club in Lowell, Massachusetts during 1980-81. Angiulo oversaw the barbooth operation, with Francesco Angiulo as the accountant, Peter Vulgaropoulus as the manager, and *5 Vincent Roberto (a/k/a "Fat Vinnie") as an assistant manager. Zannino had a financial interest. Numerous conversations were intercepted in which Zannino, Angiu-10, and others discussed the barbooth gambling business, including their stake in it, the profits collected, and the house's extension of credit to bettors. Additional evidence was garnered during a warranted search of the Lowell premises in late 1981.

As previously noted, appellant's case was severed from his eodefendants. He was tried on three of the counts against him: two counts of running illegal gambling businesses in violation of 18 U.S.C. § 1955 (relating, respectively, to poker games and barbooth gambling), and a third accusing him of making an extortionate extension of credit to Smoot in violation of 18 U.S.C. § 892(a). Appellant was convicted on all three counts.

In this appeal, he assigns myriad errors. There are four major issues: the use of Smoot's testimony; the admissibility of the tape-recorded conversations; sufficiency of the evidence; and defendant's flagship claim — that his ill health required more solicitous treatment than was received. We address these in the indicated order, touch briefly upon a few other arguments, and summarily reject the rest.

11. A DEAD MAN'S TALE

Smoot, a cooperating government witness, had been placed in the witness protection program and testified at the trial of Zannino's codefendants. On that occasion, he was vigorously cross-examined by three different defense counsel. He died prior to appellant's trial. Appellant mounts a two-pronged challenge to the judge's ruling that Smoot's earlier testimony could be introduced.

A. The Confrontation Clause.

Zannino first contends that reading Smoot's previous testimony to his jury violated the Confrontation Clause, U.S. Const. Amend. VI. To be sure, the Constitution prohibits the random admission into evidence of an unavailable declarant's hearsay statements. Yet, we know on the best authority that such out-of-court statements may nonetheless be admitted at a criminal trial in a variety of circumstances. See, e.g., Bourjaily v. United States, 483 U.S. 171, 183-84, 107 S.Ct. 2775, 2782-83, 97 L.Ed.2d 144 (1987) (coconspirator statements); Dutton v. Evans, 400 U.S. 74, 88-89, 91 S.Ct. 210, 219-20, 27 L.Ed.2d 213 (1970) (statement against penal interest); see also United States v. Seeley, 892 F.2d 1, 2 (1st Cir.1989); United States v. Fields, 871 F.2d 188, 192-93 (1st Cir.), cert. denied, — U.S. -, 110 S.Ct. 369, 107 L.Ed.2d 355 (1989); United States v. Dunn, 758 F.2d 30, 39 (1st Cir.1985).

The toúchstone is trustworthiness. When a declarant's unavailability has been shown, the Confrontation Clause may be satisfied if the declaration bears adequate "indicia of reliability." Ohio v. Roberts, 448 U.S. 56, 66, 100 S.Ct. 2531, 2539, 65 L.Ed.2d 597 (1980). Put in constitutional context, "the mission of the Confrontation Clause is to advance a practical concern for the accuracy of the truth-determining process in criminal trials by assuring that 'the trier of fact [has] a satisfactory basis for evaluating the truth of the prior statement' ". Dutton, 400 U.S. at 89, 91 S.Ct. at 220 (quoting California v. Green, 399 U.S. 149, 161, 90 S.Ct. 1930, 1936, 26 L.Ed.2d 489 (1970)). Thus, the requirements of the Confrontation Clause regarding the admission of hearsay evidence are met whenever the evidence falls within a firmly rooted exception to the hearsay principle. See Bourjaily, 483 U.S. at 182-83, 107 S.Ct. at 2782-83; Roberts, 448 U.S. at 66, 100 S.Ct. at 2539. As we recently wrote, "to the extent that a traditional hearsay exception has sufficiently long and sturdy roots, a determination that the exception applies obviates the need for a separate assessment of the indicia of reliability which may or may not attend the evidence." Puleio v. Vose, 830 F.2d 1197, 1205 (1st Cir.1987), cert. denied, 485 U.S. 990, 108 S.Ct. 1297, 99 L.Ed.2d 506 (1988).

"While a firmly rooted hearsay exception doubtless exists for former testimony given by a declarant who dies, or becomes unavailable, before the trial at issue, see *6 Mancusi v. Stubbs, 408 U.S. 204, 216, 92 S.Ct. 2308, 2314, 33 L.Ed.2d 293 (1972); California v. Green, 399 U.S. at 165-66, 90 S.Ct. at 1938-39, that exception is usually thought to hinge on defendant's counsel having had "complete and adequate opportunity to cross-examine" on the earlier occasion. Green, 399 U.S. at 166, 90 S.Ct. at 1939. Here, Zannino's trial had been severed and his counsel, therefore, had no chance to cross-question Smoot when the main racketeering trial occurred. We therefore assume, as appellant urges, but do not decide, that no such exception applies.

The presence of such a categorical exception is not, however, a sine qua non to admissibility, but merely a way of easing the introduction of an unavailable declarant's statements. Where, as here, no such exception is claimed, the court may still look at the totality of the circumstances to see if adequate indicia of reliability attend the evidence. See Bourjaily, 483 U.S. at 179, 107 S.Ct. at 2781; Roberts, 448 U.S. at 66, 100 S.Ct. at 2539; Dutton, 400 U.S. at 89, 91 S.Ct. at 219; Dunn, 758 F.2d at 39. To that end, we independently examine the circumstances surrounding Smoot's testimony in order to ascertain whether it passes sixth amendment muster.

Before embarking upon this voyage, we first address, and reject, appellant's asseveration that, absent the catharsis of cross-examination, an unavailable declarant's earlier testimony can never be reliable enough to allay constitutional concerns. While the point seems to be an open one in this circuit, our sister circuits have uniformly admitted uncrossexamined grand jury testimony into evidence at a subsequent trial where the declarant is no longer available and the requisite indicia of reliability exist. See, e.g., United States v. Guinan, 836 F.2d 350, 358 (7th Cir.), cert. denied, 487 U.S. 1218, 108 S.Ct. 2871, 101 L.Ed.2d 907 (1988); United States v. Marchini, 797 F.2d 759, 764-65 (9th Cir.1986), cert. denied, 479 U.S. 1085, 107 S.Ct. 1288, 94 L.Ed.2d 145 (1987); United States v. Walker, 696 F.2d 277, 280-81 (4th Cir.1982), ce rt. denied, 464 U.S. 891, 104 S.Ct. 234, 78 L.Ed.2d 226 (1983); United States v: Barlow, 693 F.2d 954, 963-65 (6th Cir.1982), ce rt. denied, 461 U.S. 945, 103 S.Ct. 2124, 77 L.Ed.2d 1304 (1983); United States v. Carlson, 547 F.2d 1346, 1355-60 (8th Cir.1976), cert. denied, 431 U.S. 914, 97 S.Ct. 2174, 53 L.Ed.2d 224 (1977). Although the practice seems impeccable, we need not go quite so far today.

In this case, the reliability index is higher. Before the grand jury, testimony is not cross-examined at all; here, though Zanni-no's counsel never had an opportunity to question Smoot, the declarant was vetted at the earlier trial by defense attorneys who shared appellant's interest in denigrating Smoot's credibility. The case before us is, therefore, a much stronger one for admissibility: the functional equivalent of cross-examination by the defendant was present here, bolstering the inherent reliability of the testimony. See Barker v. Morris, 761 F.2d 1396, 1402-03 (9th Cir.1985) (approving admission of testimony of deceased witness given at preliminary hearing and used at trial against defendant who was not represented at the preliminary hearing), cert. denied, 474 U.S. 1063, 106 S.Ct. 814, 88 L.Ed.2d 788 (1986). Thus, Smoot's sworn statements at the Angiulos' trial, as opposed to, say, grand jury testimony, offered a "particularized guarantee!)] of trustworthiness." Roberts, 448 U.S. at 66, 100 S.Ct. at 2539.

We rule that the absence of cross-examination on appellant's behalf does not automatically require rejection of the former testimony of an unavailable declarant in a criminal ease. Cross-examination, while it remains an important method of testing for the truth, is not the exclusive method by which the imprimatur of reliability can be conferred upon hearsay evidence. We do not believe it to be constitutionally required as a condition to the introduction of former testimony.

We now move to other indicia of reliability. Having carefully reviewed the testimony and the texture of the two trials, we agree with the district court that Smoot's former testimony contained ample trappings of dependability. The testimony *7 was given under oath. It was not implausible. It was solidly corroborated: to cite but a few examples, Francesco and Nicolo Angiulo were overheard discussing the |14,000 that Smoot owed to Zannino; subsequently, Zannino and Angiulo were heard debating what procedure might be appropriate were Smoot to default; and, on a later tape, a group of persons (including Zannino, Angiulo, and Isabella) rehashed the status of Smoot's debt and the anticipated arrangements for repayment. Such strong corroboration obviously enhances the testimony's reliability. See, e.g., United States v. Workman, 860 F.2d 140, 144-46 (4th Cir.1988), cert. denied, — U.S. -, 109 S.Ct. 1529, 103 L.Ed.2d 834 (1989); Guinan, 836 F.2d at 356-58; Marchini, 797 F.2d at 764; Barker, 761 F.2d at 1402. It is likewise relevant that Smoot testified about matters within his personal knowledge, see, e.g., Marchini, 797 F.2d at 765; that he appeared without the protection of immunity, see, e.g., Guinan, 836 F.2d at 358; and that no significant extrinsic evidence impeached his version of events.

There is no need to paint the lily. Smoot's former testimony, though not subject to cross-examination on appellant's behalf, bore such staunch hallmarks of reliability that its admission was completely compatible with the guarantees of the sixth amendment.

B. Rule 804(b)(5).

Our ruling that there was no constitutional bar to use of this evidence does not end our inquiry into it. In a criminal trial, it is never enough that certain evidence is not prohibited; the proponent must be able to show, affirmatively, that it is permitted. In this case, the nonconstitutional dispute as to admissibility focuses on Fed.R.Evid. 804(b)(5). The rule provides that statements made by an unavailable declarant— and few declarants are more "unavailable" than dead men — may nonetheless be introduced if they are accompanied by "circumstantial guarantees of trustworthiness" and if the court determines that:

(A) the statement is offered as evidence of a material fact; (B) the statement is more probative on the point for which it is offered than any other evidence which the proponent can procure through reasonable efforts; and (C) the general purposes of these rules and the interests of justice will best be served by admission of the statement into evidence.
Fed.R.Evid. 804(b)(5). We review the district court's application of the rule under an abuse-of-discretion standard. See United States v. Rodriguez, 706 F.2d 31, 41 (2d Cir.1983); Carlson, 547 F.2d at 1354-55. Applying this yardstick, we find that the court acted within its discretion in deciding that Smoot's testimony satisfied the rule's requirements.
As to "circumstantial guarantees of trustworthiness," nothing need be said. We have already found that the statements were accompanied by meaningful indicia of reliability. See supra Part 11(A). In this instance, those findings are dispositive of the "guarantees of trustworthiness" prong. Whether or not the two standards are always the same is a question we need not answer.

Turning to the rule's remaining requirements, we believe that the evidence's materiality is obvious. The record plainly indicates that Angiulo headed a loansharking business which involved Zannino, Donato Angiulo, and others, and that these individuals acted together to collect the $14,000 debt. The declarant's former testimony dealt with matters such as the circumstances surrounding the extension of credit, its terms and payment history, and the borrower's understanding that physical harm might result from nonpayment. The testimony was painfully material. It was also highly probative. Smoot had personal knowledge of the matters at issue, unique in some respects. He alone could recount his understanding of the foreseen consequences of default. With Smoot dead, his personal knowledge could best be tapped by resort to his earlier testimony. However heroic the efforts that it might undertake, the government could not be expected to procure evidence with a greater, or equivalent, probative worth. The absence of cross-examination was not fatal; noth *8 ing on the face of the rule, or in its spirit, prohibits the admission of previous testimony untested by cross-examination. 6

A dispassionate appraisal of the circumstances convinces us, as it did the lower court, that allowing the jury to hear Smoot's former testimony was consonant with both the interests of justice and the Federal Rules' general purposes. In our estimation, the panoply of factors present in this case fully satisfied the strictures of Rule 804(b)(5). See, e.g., Marchini, 797 F.2d at 764-65; Barlow, 693 F.2d at 961—62; United States v. Boulahanis, 677 F.2d 586, 588-89 (7th Cir.), cert. denied, 459 U.S. 1016, 103 S.Ct. 375, 74 L.Ed.2d 509 (1982); United States v. Garner, 574 F.2d 1141, 1144-46 (4th Cir.), cert. denied, 439 U.S. 936, 99 S.Ct. 333, 58 L.Ed.2d 333 (1978); United States v. Ward, 552 F.2d 1080, 1082-83 (5th Cir.), cert. denied, 434 U.S. 850, 98 S.Ct. 161, 54 L.Ed.2d 119 (1977). We discern no abuse of discretion in the district court's application of Fed.R. Evid. 804(b)(5) or in its admission of the challenged testimony.

III. ELECTRONIC SURVEILLANCE EVIDENCE

Zannino attacks the district court's denial of his motion to suppress the voluminous evidence obtained through electronic surveillance. He claims that suppression is warranted because the government, in its affidavit supporting the application for judicial permission to carry out the bugging of the premises, failed to reveal previous wiretap applications.

It is true that, when the government asked the federal district court for authorization to proceed in January 1981, the moving papers did not disclose the existence of five earlier applications by Massachusetts police (circa 1978) seeking to make appellant the target of electronic eavesdropping. By the same token, the record is barren of any direct evidence that the federal investigators knew of these earlier state efforts. Appellant contends, however, that the circumstances leading to his arrest in 1978 were so well known in the Boston area that, in the present investigation, federal authorities must have known that he had been the subject of court-ordered electronic surveillance some years previously. Even if the individuals responsible for conducting the current investigation did not have actual knowledge of the prior interceptions, Zannino argues, other members of the Federal Bureau of Investigation (FBI) and Strike Force unquestionably had such knowledge. The failure to make reasonable inquiry of knowledgeable persons in those agencies, he concludes, was so reckless an omission as to invalidate the surveillance which led to the instant indictment.

We start with the applicable statute, which requires that each application for electronic surveillance include:

a full and complete statement of the facts concerning all previous applications known to the individuals authorizing and making the application, made to any judge for authorization [of electronic surveillance] involving any of the same persons, facilities or places specified in the application, and the action taken by the judge on each such application.
18 U.S.C. § 2518(l)(e). The statute's plain language is, we think, the best guide to its meaning. Giving the language its ordinary purport, the only potentially disqualifying knowledge is that of "the individuals authorizing and making the application." Id. That is how the statute reads and how it has generally been interpreted. See, e.g., United States v. O'Neill, 497 F.2d 1020, 1025-26 (6th Cir.1974) (complete compliance with § 2518(l)(e) achieved where application disclosed all previous applications known to individual actors, notwithstanding that other applications existed); United States v. Harvey, 560 F.Supp. 1040, 1073 (S.D.Fla.1982) (similar), aff'd, 789 F.2d 1492 (11th Cir.), cert. denied, 479 U.S. 854, 107 S.Ct. 190, 93 L.Ed.2d 123 (1986).

*9 In this case, the district court held a pretrial suppression hearing. Collins, the Strike Force attorney who applied for the surveillance warrants, and the affiants in connection therewith (FBI agents Quinn and Rafferty), all testified that, at the time, they were unaware of the local authorities' 1978 applications. The district court credited this testimony. We review this finding only for clear error — and can discern none. That, it would seem, should end the matter: an investigator cannot be expected to disclose something he or she does not know. Section 2518(l)(e) requires government agents to be forthcoming, not omniscient.

Undeterred, appellant urges that, even if the agents were uninformed, they were chargeable with constructive knowledge. The short answer to this plaint is that the statute requires actual, not constructive, knowledge. The slightly longer answer is that, even if the government may not "recklessly remain ignorant of previous applications," United States v. Sullivan, 586 F.Supp. 1314, 1318 (D.Mass.1984) — an idea we leave for another day — there was no evidence of willful blindness here. At best, appellant showed the possibility of a negligent, but unintentional, violation of 18 U.S.C. § 2518(l)(e): the agents testified that they conducted a thorough inspection of FBI files to determine whether there were any prior applications for electronic surveillance directed at Zannino or other proposed targets, and came up empty. If they were careless, and erred, it profits appellant naught. Mere negligence would not warrant suppression of the evidence. See United States v. Abramson, 553 F.2d 1164, 1169-70 (8th Cir.), cert. denied, 433 U.S. 911, 97 S.Ct. 2979, 53 L.Ed.2d 1095 (1977); see also United States v. Giordano, 416 U.S. 505, 527, 94 S.Ct. 1820, 1832, 40 L.Ed.2d 341 (1974) (indicating that suppression of evidence would be justified only if electronic surveillance violation contravened "those statutory requirements that directly and substantially implement the congressional intention to limit the use of intercept procedures to those situations clearly calling for the employment of this extraordinary investigative device"); cf. United States v. Mora, 821 F.2d 860, 870 (1st Cir.1987) (evidence obtained through wiretaps was admissible at defendants' trial even though tapes were not judicially sealed in strict accordance with 18 U.S.C. § 2518(8)(a)).

Because the record amply supports the district court's finding that the responsible government officials were unaware, after a good faith inquiry, of the earlier state applications for electronic surveillance, the disclosure requirements of section 2518(l)(e) were not flouted. The motion to suppress was properly rebuffed. 7

IV. SUFFICIENCY OF THE EVIDENCE

While tacitly admitting the sufficiency of the evidence on count one of the redacted indictment (which involved his role in the North Margin St. poker games), appellant raises a sufficiency challenge to counts two and three. Our task is to determine whether any rational jury, taking the evidence in its totality and in the light most flattering to the government, could have found appellant guilty beyond a reasonable doubt. See Cintolo, 818 F.2d at 983. The evidence, of course, must be sufficient as to each essential element of the crime charged.

A. Barbooth Gambling.

As to count two, appellant takes a rifle-shot approach: he effectively concedes the legal adequacy of the government's proof in most respects, but asserts that the prosecution did not show that at least five persons were involved in conducting the unlawful barbooth gambling. Appellant is shooting blanks.

We start by observing that the five person minimum is expressly made an element of the offense with which Zannino was *10 charged. 8 In the lexicon of section 1955, the term "conduct" embraces all who participate in the operation of the specified gambling business, that is, each and every person who performs any act, function, or duty necessary or helpful in the business' ordinary operation. As we read it, the statute of conviction applies even to individuals who have no role in managing or controlling the business and who do not share in its profits. Cf Joshua 9:21 (discussing "hewers of wood and drawers of water"). In sum, section 1955 proscribes any type or degree of participation in an illegal gambling business, except participation as a mere bettor. Sanabria v. United States, 437 U.S. 54, 70-71 n. 26, 98 S.Ct. 2170, 2182 n. 26, 57 L.Ed.2d 43 (1978); United States v. DiMuro, 540 F.2d 503, 508 (1st Cir.1976), cert. denied, 429 U.S. 1038, 97 S.Ct. 733, 50 L.Ed.2d 749 (1977). Once this coign of vantage is established, the dampness of appellant's powder becomes readily apparent.

Based on tape recorded conversations and other evidence, the government's expert witness, Daly, testified that at least five persons were involved "in the managing, financing or running of [the] barbooth game from at least Christmas of 1980 through March of 1981." He identified the five as Angiulo, Zannino, Francesco Angiulo, Vulgaropoulus, and Roberto, and described their roles in the enterprise. Appellant wastes little time on the first four— and with good reason; the evidence as to them was plenteous. He trains his guns instead on Roberto's inclusion, assailing the admission of Daly's testimony and denigrating the government's ancillary evidence. The volley misfires.

The court's allowance of Daly's opinion evidence cannot be faulted. See United States v. Ladd, 885 F.2d 954, 959 (1st Cir.1989) (discussing trial judge's discretion in determining both admissibility of expert testimony and particular expert's qualifications); United States v. Hoffman, 832 F.2d 1299, 1310 (1st Cir.1987) (similar); see also United States v. Lamattina, 889 F.2d 1191, 1194 (1st Cir.1989). The jury, we think, was entitled to consider Daly's testimony and assess its credibility and probative value in light of all the evidence. Furthermore, Daly's testimony seems sufficiently record-rooted to sustain a finding that Roberto participated in operating the barbooth game.

Our conclusion concerning the adequacy of the proof anent Roberto's complicity, and thus, Zannino's guilt, is bulwarked by the other evidence corroborating Roberto's involvement. We offer a representative sampling:

1. Roberto was at North Margin St. no less than five times during the surveillance period.

2. Roberto, testifying as a defense witness, admitted being at the Demosthenes Club on various occasions in 1980-81 while barbooth was being played. (Although he said he was merely a player, the jury was not bound to believe that aspect of his story.)

3. In a February 1981 conversation, Zannino told Angiulo that he was sending for Roberto and Roberto's "partner," Vul-garopoulus, to resolve a discrepancy regarding the profits from the barbooth gambling business.

4. In a March 1981 conversation, Zanni-no and Angiulo gloated over the money that Roberto was bringing them from the game.

5. In November 1981, Vulgaropoulus and Roberto were arrested when state authorities raided the barbooth game. Gambling paraphernalia was seized on that occasion.

Viewing this evidence in conjunction with Daly's testimony, a rational jury could easily have found, beyond any reasonable doubt, that Roberto performed a necessary, or at least facilitative, role in the ordinary *11 operation of the barbooth gambling business.

B. Loansharking.

Appellant also asserts that there was insufficient evidence to sustain his conviction under 18 U.S.C. § 892(a). He notes that the statute requires that loans, to be extortionate, be made in a climate of fear — fear that "violence or other criminal means" will follow hard upon nonpayment 9 — and he claims that there is no proof that he and the borrower, Smoot, reached a mutual understanding that physical harm could ensue if timely payments were not forthcoming on the $14,000 debt. While appellant is correct that the understanding of both creditor and debtor is crucial to proving a substantive violation of 18 U.S.C. § 892(a), see United States v. DeVincent, 546 F.2d 452, 454-56 (1st Cir.1976), ce rt. denied, 431 U.S. 903, 97 S.Ct. 1694, 52 L.Ed.2d 387 (1977), his argument nevertheless fails.

Congress recognized that it might be difficult to prove the understanding of the creditor directly. Thus, the lawmakers went on to provide that "if it is shown that all of the following factors were present in connection with the extension of credit in question, there is prima facie evidence that the extension of credit was extortion-ate_" 18 U.S.C. § 892(b). The statute enumerated four factors: (1) that repayment is unenforceable through civil judicial processes; (2) that the loan requires interest greater than 45% per year; (3) that the loan exceeds $100; and (4) that the debtor reasonably believes that the lender either has used extortion to collect other debts or has a reputation for doing so. See 18 U.S.C. §§ 892(b), (c); see generally United States v. Dennis, 625 F.2d 782, 800-01 (8th Cir.1980); United States v. Annoreno, 460 F.2d 1303, 1308-09 (7th Cir.), cert. denied, 409 U.S. 852, 93 S.Ct. 64, 34 L.Ed.2d 95 (1972). In effect, the statute creates a rebuttable presumption, triggered by proof of the statutory factors. See United States v. Martorano, 557 F.2d 1, 8 n. 3 (1st Cir.1977), cert. denied, 435 U.S. 922, 98 S.Ct. 1484, 55 L.Ed.2d 515 (1978). Here, the requisite understanding of both creditor and debtor was satisfactorily established by objective evidence verifying the existence of the first three factors; by Smoot's testimony as to his beliefs; and by a demonstration, founded upon the totality of the evidence, that Smoot's fears were reasonable under the circumstances.

We need hardly pause over the introductory triad. Smoot's $14,000 debt was incurred in the course of illegal gambling activity; it was never reduced to writing; it was obviously unenforceable through the usual judicial channels; and it carried a usurious interest rate of at least 52% per annum. 10 The evidence as to Smoot's expressed fears seems self-explanatory: Smoot testified that he believed Zannino to be Cincotti's boss; he knew Donato Angiu-lo's reputation for violence; and he feared the use of force if he did not make his scheduled payments. The plausibility of Smoot's trepidation cannot seriously be doubted. Evidence of a defendant's nexus to organized crime can be taken into account in evaluating reasonableness of a debtor's fears, see DeVincent, 546 F.2d at 456-57, and Zannino's own statements — he boasted incessantly about his reputation as a loanshark and his use of violence and threats to collect indebtednesses — established that he was a Capo Regime in the Patriarca Family. Smoot testified that, during the pendency of the debt, he was acutely aware of the reputation for vio- *12 lenee possessed by both Zannino and Zanni-no's "collector," Donato Angiulo. Smoot knew of their involvement in organized crime and knew that he could be threatened with physical harm if he failed to make timeous repayments.

Given the statutory framework, the jury was unquestionably entitled to infer that, at the relevant times, Zannino and Smoot had a mutual understanding that physical harm could befall the latter if he delayed or defaulted in squaring his account with the former. The essential elements of the crime were proven.

V. ZANNINO'S HEALTH

The cornerstone upon which Zannino's appeal rests is a claim that the district court abused its discretion by denying a motion to postpone his trial indefinitely. As a spinoff of this asseveration, appellant says that he was also prejudiced in that, as the trial proceeded, his physical and mental condition deteriorated to the point where he could not testify and was thus deprived of his constitutional right to aid his defense and present witnesses on his own behalf. We have combed the record and discovered more cry than wool.

A. Setting the Stage.

Zannino was hospitalized in 1977, having sustained a myocardial infarction, preceded by angina pectoris and congestive heart failure. During the next two years, he was hospitalized twice more; consequently, he was found unable to stand trial in a gambling prosecution unrelated to the instant case. He was readmitted to the hospital several times from early 1981 to mid-1983 due to chest pains and other symptoms. In September 1983, on the very day that the instant indictment was returned, appellant was hospitalized, complaining of chest pain. He was discharged in January 1984. The discharge diagnosis read: "Atherosclerotic heart disease, unstable angina pectoris, history of myocardial infarction, coronary insufficiency and congestive heart failure." Other brief hospitalizations followed. He continued under medical supervision.

Zannino moved to continue the racketeering trial, citing his ill health. Following an evidentiary hearing, the district court found in June 1985 that the likelihood of myocardial infarction, high grade ventricular arrhythmia, or cardiac arrest were, in fact, remote. The court also found Zanni-no's angina and congestive heart failure to be treatable and controllable with proper medication and diet. The court noted that Zannino was to some extent responsible for exacerbating his health problems by failing either to follow prescribed diet or to take medication on schedule. The court concluded that, on balance, Zannino was able to stand trial.
The case against Zannino and his code-fendants subsequently went forward. A jury was selected. On the day that opening statements began (July 10, 1985), appellant was again hospitalized. Six days later, he suffered a second myocardial infarction. With the government's consent, his case was severed from the ongoing trial of his codefendants. That trial lasted until February 28, 1986.

Meanwhile, the district court monitored Zannino's medical condition in connection with both his ability to stand trial and his eligibility for pretrial release. Much of what transpired has been described before, see United States v. Zannino, 798 F.2d 544, 545 (1st Cir.1986) (per curiam), so we can be succinct. It suffices to observe that the medical opinions conflicted. Evidentia-ry hearings were held. Eventually, a panel of three renowned cardiologists reviewed Zannino's medical records at the district court's request and submitted a report. The judge then forwarded certain supplementary materials to the panel and posed some follow-up questions. In August 1986, the panel issued another report. Collectively, the reports (both of which were unanimous) concluded that Zannino suffered from chronic coronary heart disease, not likely to improve, and had experienced myocardial infarctions and angina pectoris. Zannino was likely to undergo periodic bouts of chest discomfort regardless of whether he was on trial. The physicians noted, however, that the "vast majority of episodes of 'chest discomfort' ... are rapid *13 ly relieved by oral medication [and are] not usually life threatening" and thus, "could be rapidly diagnosed as not requiring hospitalization." A lengthy trial would be likely to increase the frequency of such episodes; a shorter, less intense trial would be safer. The panel recommended certain precautions if such a trial were to occur: abbreviated trial days; periodic mid-trial medical examinations; continuous monitoring by electrocardiogram while in the courtroom; instant availability of emergency medications and supplies (including oxygen and a defibrillator); and the presence of medical personnel at the trial. The panel also suggested that Zannino be tried alone.

After reviewing the reports and balancing competing considerations, the district court concluded that, given the gravity of the charges and the permanent nature of Zannino's illness, the government's interest in trying Zannino outweighed the personal risks inherent in a specially tailored trial. Those risks, in the court's view, could be substantially reduced by a shorter trial on fewer charges, conducted under prophylactic conditions. To that end, the judge severed the most complex charges against Zannino (e.g., racketeering by means of a continuing criminal enterprise), adopted the physicians' recommendations as to procedure and special arrangements in to to, denied the motion for an indefinite postponement, and ordered Zannino to stand trial on the three specific offense counts which we have discussed. The trial went forward on January 27,1987 and lasted about a month. 11

B. Failure to Postpone.

A district court's decision to deny a continuance can be disturbed on appeal only for abuse of discretion. Morris v. Slappy, 461 U.S. 1, 11-12, 103 S.Ct. 1610, 1616-17, 75 L.Ed.2d 610 (1983); Real v. Hogan, 828 F.2d 58, 63 (1st Cir.1987); see also Note, A Capital Defendant's Right to a Continuance Between the Two Phases of a Death Penalty Trial, 64 N.Y.U.L.Rev. 579, 593 (1989) (district judge's discretion to deny a continuance is limited only where refusal to grant more time infringes upon a constitutional right). Moreover, in a case where a continuance request is predicated on medical dangerousness, the judge must be given a relatively wide berth. He has firsthand knowledge of the defendant and his situation, gained over time; he knows the courtroom conditions and the circumstances of trial intimately, and possesses great familiarity with the scope and complexity of the litiga-ble issues; he has the ability to question health care providers and solicit additional opinions; he can best sift overstatement from understatement, eyeing the defendant's and the doctors' credibility, and tempering the prosecutors' zeal; and he will usually have developed a "feel" for factors like intensity and stressfulness. We believe it is perilous for an appellate tribunal, traversing the frozen tundra of an inert record, to secondguess the trial judge's informed synthesis of the relevant integers which enter into so ramified an equation. See United States v. Bernstein, 417 F.2d 641, 643 (2d Cir.1969) ("The determination of competence to stand trial is basically a question of fact; [and] the trial judge is in a better position to resolve it than the appellate courts.").

While we give deference to the district court's assessment, we do not owe it blind allegiance. We look to see whether the court below had evidence before it which was, qualitatively and quantitatively, sufficient to support the decision which it reached. See United States v. Alexander, 869 F.2d 808, 811 (5th Cir.1989); United States v. Brown, 821 F.2d 986, 988 (4th Cir.1987); Bernstein, 417 F.2d at 643; see also Independent Oil and Chemical Workers of Quincy, Inc. v. Procter & Gamble Mfg. Co., 864 F.2d 927, 929 (1st Cir.1988) (stating test for abuse of discretion). The mere possibility of an adverse effect on a party's wellbeing is not enough to warrant a postponement. We agree with the Fourth Circuit that "the medical *14 repercussions must be serious and out of the ordinary; the impending trial must pose a substantial danger to a defendant's life or health." Brown, 821 F.2d at 988. Throughout, we bear in mind that our function is one of review, not of independent evaluation: if the evidence can, on balance, fairly sustain either of two plausible conclusions, and the lower court chose one, we have no right to interfere.

Because circumstances vary so widely, we can present no all-inclusive checklist of the factors which bear on such a determination. When a colorable claim of medical dangerousness is lodged and contested, the court must carefully investigate the situation, assemble the pertinent data, and then consider not only the medical evidence but also the defendant's activities (in the courtroom and outside of it), the steps defendant is taking (or neglecting to take) to improve his health, and the measures which can feasibly be implemented to reduce medical risks. Once a dangerousness quotient is established, the judge must weigh the foreseeable risks against the demonstrable public interest, taking into account factors such as the severity of the charges and the extent of the government's interest in trying the defendant. If the perceived risks overbalance the perceived benefits, a continuance must be granted.

In the case at bar, we note approvingly that the court gave appellant ample time to allow his condition to ameliorate or stabilize. The court also took elaborate pains to gather the best information and opinions obtainable: the parties were allowed full rein to present their evidence; the judge then solicited assessments from three eminent (and detached) cardiologists. The court considered the medical opinions, the defendant's activities, the foreseeable risks (including the fact that a trial would doubtless subject Zannino to considerable emotional strain, thus aggravating his angina attacks and perhaps exacerbating other health problems) 12 , the nature of the charges, their separability, the public interest in a trial, the defendant's right to assist in his own defense, the prospect that more time might alter the scales' angle, and a series of intangibles. All in all, the court appears to have weighed the correct factors. The question then becomes whether, in constructing the balance, the court committed a meaningful error in judgment. See Independent Oil and Chemical Workers, 864 F.2d at 929 (so long as the proper factors have been considered, judicial discretion is abused only if "the court makes a serious mistake in weighing them").

We review the district judge's findings and the balance he struck. The judge found that Zannino would have chest pains whether or not he was in court; that, in all likelihood, his angina attacks could be palliated by oral medication; and that such attacks, although potentially serious if not relieved, were not life threatening. The judge noted that much of the maintenance of defendant's health was in his own hands; he was responsible for monitoring his diet and medication in order to avoid untoward consequences. The court fully considered the ravages of trial and concluded that, while a trial "would increase the risk of [Zannino's] sustaining another life threatening coronary incident in some degree that is neither trivial nor precisely measurable," the danger was not undue. And the court found that the public interest in bringing Zannino to trial was great.

In addition, the district court took substantial steps to reduce the medical risks incident to trial. First, it ordered Zannino tried alone and severed most of the charges against him, leaving only three. These three were handpicked to create both a *15 shorter trial and one likely to curtail wear and tear on the defendant (emotional as well as physical). 13 Second, the normal trial day and week were abbreviated. Third, special medical safeguards were made available, including provisions for periodic medical examinations during trial, continuous coronary monitoring, and on-the-spot accessibility to medical equipment. Two emergency medical technicians were in attendance during court sessions. An ambulance was parked in the courthouse garage. These precautions not only minimized the chance that a tragedy would occur, but must have served to ease the defendant's health-related concerns.

We acknowledge that a stand-trial determination in the case of an ailing defendant is among the most problematic that a federal district judge is called upon to make. "Whether a defendant's physical condition is so poor as to require a continuance or severance is not only a difficult determination ..., but it is one which carries with it the tremendous responsibility of weighing the invariably unpredictable factor of defendant's health against the government's, indeed the public's, legitimate interest in a fair and speedy disposition." Bernstein v. Travia, 495 F.2d 1180, 1182 (2d Cir.1974). A criminal trial is by its nature ordealistic — but that fact alone cannot abrogate the pronounced public interest in bringing promptly to book those accused of high crimes and felonies. See id. In this case, the crimes charged were of the gravest order and the defendant's involvement was alleged to be at the uppermost level. His medical condition was unlikely to improve, rendering a continuance functionally equivalent to a permanent ban against trial. In ordering Zannino into the dock, the court below carefully evaluated these factors and the other pertinent considerations; tailored the charges to fit the defendant's physical and emotional resources; and utilized critical firsthand impressions that we lack. We cannot say that the district judge— whose thoroughness resonates from every page of the record pertaining to this issue — misused his broad discretion.

Because the dangerousness quotient, though palpable, was not excessive, the denial of appellant's motion for a continuance was permissible. See, e.g., Alexander, 869 F.2d at 811 (trial judge's reasoned determination that defendant was physically able to testify in his own behalf and stand trial must prevail absent abuse of discretion); United States v. Pastor, 557 F.2d 930, 939 (2d Cir.1977) (where defendant suffered from angina pectoris but trial judge had implemented sufficient safeguards, deference was justified); Travia, 495 F.2d at 1182 (similar); see also Brown, 821 F.2d at 989. The perceptible risks inherent in a specially-structured trial did not overbalance the perceptible benefit to the public.

C. Deleterious Effects of Trial.

Appellant also asserts that his health deteriorated under the strain of trial, creating a special sort of prejudice. The thesis runs along the following lines: in his opening statement, defense counsel, not knowing how the vagaries of trial would affect a sick man, told the jury that Zannino's testimony was crucial to an understanding of the case; due to failing health, however, Zannino proved unable to testify when it came time for the defense case; thus, the jury, expecting to hear Zannino's testimony, most probably held his failure to testify against him. In this way, appellant says that he was deprived of due process.

We find this logomachical frock gaping at several seams. Most critically, there is not a shred of evidence that Zannino's condition worsened to the point where he became medically unable to testify. There was excellent reason, tactically, for Zanni-no to avoid the witness stand. That he decided not to testify, and that his counsel intimated to the jury that his health precluded him from testifying, is a far cry from proving either the claimed deterioration or the etiology of the decision to stay *16 off the witness stand. No further medical evidence was presented during the course of the trial and no change in circumstances was shown. On these facts, the assignment of error is infirm.

There is also a second reason why the initiative collapses. We have scoured the record without unearthing any indication that the defense made a motion for mistrial, or any other appropriate relief, at the point when Zannino "believed" that he could no longer testify. In our view, appellant's present claim is toppled by his neglect to ask for a further continuance, or a mistrial, to meet the supposed exigency of which he now complains. Cf., e.g., United States v. Diaz-Villafane, 874 F.2d 43, 47 (1st Cir.), cert., denied, — U.S. -, 110 S.Ct. 177, 107 L.Ed.2d 133 (1989); United States v. Ingraldi, 793 F.2d 408, 413 (1st Cir.1986). If there was a legitimate problem, it was incumbent upon Zannino to bring it to the trial court's attention in a timely fashion and ask for concinnous relief. The failure to do so constitutes a waiver.

VI. POTPOURRI

We touch briefly upon certain other points raised by appellant, none of which requires extended comment.

A. Severance.

After the district court narrowed the scope of trial to the three counts described supra, appellant moved for a further severance, alleging misjoinder. Fed. R.Crim.P. 8(a), 14. The district court denied the motion. Zannino polemizes against the ruling, but to no avail.

Rule 8(a) authorizes joinder of offenses if they "are of the same or similar character or are based on the same act or transaction or on two or more acts or transactions connected together or constituting parts of a common scheme or plan." All of the three offenses involved here were alleged by the Grand Jury to be predicate acts committed in furtherance of the racketeering enterprise and conspiracy. This court, and other courts of appeals, have consen-tiently held that offenses committed pursuant to the same (charged) racketeering enterprise and conspiracy may be joined in a single indictment since, in the terminology of Rule 8(a), they are based on "two or more acts or transactions connected together or constituting parts of a common scheme or plan." See, e.g., United States v. Doherty, 867 F.2d 47, 63 (1st Cir.), cert. denied, — U.S. -, 109 S.Ct. 3243, 106 L.Ed.2d 590 (1989); United States v. Kragness, 830 F.2d 842, 861-62 (8th Cir.1987); United States v. Williams, 809 F.2d 1072, 1085-86 (5th Cir.), cert. denied, 484 U.S. 896, 108 S.Ct. 228, 98 L.Ed.2d 187 (1987); United States v. Caporale, 806 F.2d 1487, 1510 (11th Cir.1986), cert. denied, 482 U.S. 917, 107 S.Ct. 3191, 96 L.Ed.2d 679 (1987). The happenstance that appellant was not tried on the RICO count did not alter the calculus; indeed, the same joinder principle applies even if the RICO offense was not charged against the particular defendant. See United States v. Manzella, 782 F.2d 533, 539-40 (5th Cir.), cert. denied, 476 U.S. 1123, 106 S.Ct. 1991, 90 L.Ed.2d 672 (1986); United States v. Weisman, 624 F.2d 1118, 1129 (2d Cir.), cert. denied, 449 U.S. 871, 101 S.Ct. 209, 66 L.Ed.2d 91 (1980).

Not only were the three counts properly joined, but appellant has not made the requisite showing of prejudice to warrant separating them. Given the trial court's precise instructions, the relative simplicity of the evidence, and the fact that Zannino was tried alone, it borders on the frivolous to claim that the failure to isolate the three residual charges from each other deprived him "of a fair trial, resulting in a miscarriage of justice." United States v. Arruda, 715 F.2d 671, 679 (1st Cir.1983); see also United States v. Walker, 706 F.2d 28, 30 (1st Cir.1983); Fed.R.Crim.P. 14. There was no misuse of the district court's considerable discretion.

B. Evidence Admitted.

Appellant contests the introduction of certain tape-recorded conversations. We need not flog a moribund mare; having reviewed his contentions and the indicated conversations, we find that the challenged *17 recordings were sufficiently relevant so as to be admissible in the trier's discretion. That being so, the district court was required to strike a balance between probative worth and likely prejudice. See Fed.R. Evid. 403. Our perscrutation of the nisi prius roll reveals no reason to disrupt the lower court's calibration of the scales. "Only rarely — and in extraordinarily compelling circumstances — will we, from the vista of a cold appellate record, reverse a district court's on-the-spot judgment concerning the relative weighing of probative value and unfair effect." Freeman v. Package Machinery Corp., 865 F.2d 1331, 1340 (1st Cir.1988). This is not the rare case.

Zannino also complains about the jury having heard evidence of an earlier extortionate scheme which he allegedly operated in concert with Thomas Peachie and Carmen Tortora. The complaint is jejune. The jury was entitled to find, from appellant's own mouth, that he was in league with Peachie and Tortora. The earlier scheme was reasonably proximate in time to the charged extortion. 14 And we, like the district court, believe that the material was competent, under Fed.R.Evid. 404(b), to show Zannino's criminal intent and extortionate understanding vis-a-vis the Smoot loan. See, e.g., United, States v. Rodriguez-Estrada, 877 F.2d 153, 156 (1st Cir.1989); United States v. Pepe, 747 F.2d 632, 670-71 (11th Cir.1984); United States v. Zeuli, 725 F.2d 813, 816-17 (1st Cir.1984); see generally Huddleston v. United States, 485 U.S. 681, 108 S.Ct. 1496, 99 L.Ed.2d 771 (1988).

C. Incorporation by Reference.

As mentioned earlier, see supra note 1, defendant's appeal was consolidated for oral argument with appeals prosecuted by the Angiulos and Granito. In a cursory reference in his appellate brief, Zannino seeks to "adopt[] all of the arguments made on behalf of co-defendants Gennaro, Donato and Michele Anguilo [sic], and co-defendant Samuel Granito, as each argument applies to this appellant." We summarily reject this ploy. The codefendants were tried apart from Zannino, on a somewhat different array of charges. They have raised a series of issues which relate to their separate trial in ways not readily transferrable to Zannino's circumstances.

Perhaps more important, we see no reason to abandon the settled appellate rule that issues adverted to in a perfunctory manner, unaccompanied by some effort at developed argumentation, are deemed waived. See, e.g., Brown v. Trustees of Boston Univ., 891 F.2d 337, 353 (1st Cir. 1989); Leer v. Murphy, 844 F.2d 628, 634 (9th Cir.1988). It is not enough merely to mention a possible argument in the most skeletal way, leaving the court to do counsel's work, create the ossature for the argument, and put flesh on its bones. As we recently said in a closely analogous context: "Judges are not expected to be min-dreaders. Consequently, a litigant has an obligation 'to spell out its arguments squarely and distinctly,' or else forever hold its peace." Rivera-Gomez v. de Castro, 843 F.2d 631, 635 (1st Cir.1988) (quoting Paterson-Leitch Co. v. Massachusetts Municipal Wholesale Elec. Co., 840 F.2d 985, 990 (1st Cir.1988)).

VII. CONCLUSION

We need go no further. Our scrutiny of the case persuades us that all of Zannino's contentions must be rejected. No significant legal error appearing, appellant's convictions and his sentence must be

Affirmed.""")

# Case 10
add_case("""Immigration & Naturalization Service v. Bagamasbad
Supreme Court of the United States

Citations: 429 U.S. 24, 97 S. Ct. 200, 50 L. Ed. 2d 190, 1976 U.S. LEXIS 169
Docket Number: 75-1666
Judges: Per Curiam
Opinion
Authorities (8)
Cited By (1K)
Summaries (493)
Similar Cases (7.1K)
PDF
Headmatter
IMMIGRATION AND NATURALIZATION SERVICE v. BAGAMASBAD

No. 75-1666.
Decided November 1, 1976
Combined Opinion
Per Curiam.
Repondent, an alien who had overstayed her tourist visa by four yéars, applied to have her status adjusted to that of permanent resident alien pursuant to 8 U. S. C. § 1255 (a). That section authorizes the Attorney General in his discretion to change the status of an alien who is physically present in the United States to that of a permanent resident, but only if, among other things, the alien would be eligible for an immigrant visa and admissible into the United States as a permanent resident. * The District Director of the Immigration *25 and Naturalization Service (INS) denied respondent's application as a matter of discretion because she had made serious misrepresentations to the United States consul who had issued her visa. For the same reasons, the immigration judge presiding at a later deportation hearing also declined to exercise his discretion in her favor. Neither the District Director nor the immigration judge addressed himself to whether respondent satisfied the specific statutory requirements for permanent residence. The Board of Immigration Appeals affirmed, finding that the circumstances fully supported the discretionary denial of relief and concluding that "the immigration judge could properly pretermit the question of statutory eligibility and deny the application ... as an exercise of discretion."

A divided Court of Appeals sitting en banc held that although the immigration judge had properly exercised his discretion to deny respondent's application, the statute required the judge to make findings and reach conclusions with respect to respondent's eligibility for admission into this country as a permanent resident. 531 F. 2d 111 (CA3 1976). Disagreeing as we do with the Court of Appeals, we grant the petition for certiorari filed by the INS and the motion by respondent to proceed in forma pauperis and reverse the judgment of the Court of Appeals.

As a general rule courts and agencies are not required to make findings on issues the decision of which is unnecessary to the results they reach. Hirabayashi v. United States, 320 U. S. 81, 85 (1943); Silva v. Carter, 326 F. 2d 315 (CA9 1963), *26 cert. denied, 377 U. S. 917 (1964); Goon Wing Wah v. INS, 386 F. 2d 292 (CA1 1967); De Lucia v. INS, 370 F. 2d 305, 308 (CA7 1966), cert. denied, 386 U. S. 912 (1967). Here, it is conceded that respondent's application would have been properly denied whether or not she satisfied the statutory eligibility requirements. In these circumstances, absent an express statutory requirement, we see no reason to depart from the general rule and require the immigration judge to arrive at purely advisory findings and conclusions as to statutory eligibility.

In arriving at its contrary conclusion, the Court of Appeals relied on a dictum in Jay v. Boyd, 351 U. S. 345 (1956), which involved a similar provision, 8 U. S. C. § 1254 (a), authorizing the Attorney General in his discretion to grant relief from deportation if certain eligibility requirements are met. In the course of affirming the discretionary denial of relief, the Court indicated that the statute entitled the applicant to a ruling on his eligibility. But the statement followed a reference to immigration regulations which then expressly required a determination of eligibility in each case. 351 U. S., at 352-353. These regulations have been superseded, and the regulation applicable to this case has no such requirement. 8 CFR §242.18 (a) (1976).

The Court of Appeals also thought it advisable to require the making of eligibility findings in 8 U. S. C. § 1255 (a) proceedings to foreclose the possibility that a United States consul to whom an alien might later apply for an immigration visa would mistakenly construe the immigration judge's exercise of discretion as a finding of statutory ineligibility binding on the consul. But the basis for the immigration judge's action must be set forth in writing under 8 CFR § 242.18 (a) (1976). Where, as here, his action is discretionary, it will be clear to any United States consul that no eligibility determination has been made. The consul will be free to give such findings as have been made their appropriate *27 weight, if any, see Cartier v. Secretary of State, 165 U. S. App. D. C. 130, 137, 506 F. 2d 191, 198 (1974), cert. denied, 421 U. S. 947 (1975); Talavera v. Pederson, 334 F. 2d 52, 57 (CA6 1964), and to make his own legal judgment on eligibility.

The judgment of the Court of Appeals is reversed.
So ordered.""")

# Case 11
add_case("""FUENTES
Board of Immigration Appeals

Citations: 19 I. & N. Dec. 658
Docket Number: ID 3065
Opinion
Authorities (5)
Cited By (43)
Summaries (41)
Similar Cases (39K)
PDF
Syllabus
FUENTES, 19 I&N Dec. 658 (BIA 1988) ID 3065 (PDF) (1) Dangers which arise from the nature of employment as a policeman in an area of domestic unrest (e.g., attacks because they are viewed as extensions of a government's military forces) do not support a claim of a well-founded fear of "persecution" within the scope of section 208 of the Immigration and Nationality Act, 8 U.S.C. § 1158 (1982). (2) If policemen or guerrillas are considered to be victims of persecution based solely on an attack by one against the other, virtually all participants on either side of an armed struggle could be characterized as "persecutors" of the opposing side and would thereby be ineligible for asylum or withholding deportation. (3) Status as a former policeman is an immutable characteristic, and mistreatment occurring because of such status in appropriate circumstances could be found to be persecution on account of political opinion or membership in a particular social group. (4) Although an applicant for asylum, who claims he may be subject to persecution because of his status as a former policeman, need not establish the exact motivation of a "persecutor" where different reasons for actions are possible, he does bear the burden of establishing facts on which a reasonable person would fear that the danger arises on account of his race, religion, nationality, membership in a particular social group, or political opinion. (5) Even if an asylum claim is assumed to be otherwise demonstrated, eligibility for asylum based on nongovernmental action may not be adequately established where the evidence of danger is directed to a very local area in the country of nationality.
Combined Opinion
Interim Decision #3065




                           MATTER OF FUENTES

                         In Deportation Proceedings

                                   A-24841098

                      Decided by Board April 18, 1988

(1)Dangers which arise from the nature of employment as a policeman in an area
  of domestic unrest (e.g., attacks because they are viewed as extensions of a govern-
  ment's military forces) do not support a claim of a well-founded fear of "persecu-
  tion" within the scope of section 208 of the Immigration and Nationality Act, 8
  U.S.C. § 1158 (1982).
(2)If policemen or guerrillas are considered to be victims of persecution based solely
  on an attack by one against the other, virtually all participants on either side of
  an armed struggle could be characterized as "persecutors" of the opposing side
  and would theieby be ineligible fur asylum or withholding of deportation.
(3)Status as a former policeman is an immutable characteristic, and mistreatment
  occurring because of such status in appropriate circumstances could be found to
  be persecution on account of political opinion or membership in a particular social
  group.
(4)Although an applicant for asylum, who claims he may be subject to persecution
  because of his status as a former policeman, need not establish the exact motiva-
  tion of a "persecutor" where different reasons for actions are possible, he does
  bear the burden of establishing facts on which a reasonable person would fear
  that the danger arises on account of his race, religion, nationality, membership in
  a particular social group, or political opinion.
(5)Even if an asylum claim is assumed to be otherwise demonstrated, eligibility for
  asylum based on nongovernmental action may not be adequately established
  where the evidence of danger is directed to a very local area in the country of
  nationality.
CHARGE:
 Order: Act of 1952—Sec. 241(aX2) [8 U.S.C. § 1251(aX2)]—Entered without inspec-
                     tion
ON BEHALF OF RESPONDENT:                           ON BEHALF OF SERVICE:
 Vincent J. Agresti, Esquire                        David Dixon
 56-58 Ferry Street                                 Appellate Counsel
  Newark, New Jersey 07106


BY: Milhollan, Chairman; Dunne, Morris, Vacca, and Heilman, Board Members

                                        CKI2
                                            Interim Decision #3065

  In a decision dated August 14, 1984, the immigration judge found
the respondent deportable as charged, denied his applications for
asylum and withholding of deportation, but granted him voluntary
departure. The respondent has appealed from that decision. The
appeal will be dismissed.
  The respondent is a 33-year-old native and citizen of El Salvador
who entered the United States in 1982 without inspection. He con-
ceded deportability at his hearing. The sole issue on appeal con-
cerns his eligibility for asylum and for withholding of deportation.
  The respondent maintains that he will be persecuted and harmed
by leftist insurgents in El Salvador on account of his association
with the Government of El Salvador. He testified that he was a
member of the national police in El Salvador from 1967 to 1980 and
a guard at the United States Embassy from 1980 until 1982. In
both capacities, the respondent and his fellow officers were at-
tacked by guerrillas on several occasions. In one incident, for exam-
ple, while checking the highways, guerrillas assaulted his police
group and killed one of his fellow officers. On another occasion,
four guerrillas in an automobile machine-gunned the Embassy
while he was standing guard. When the guerrillas returned for a
second attack, they were captured.
  The respondent further testified that many inhabitants of his
hometown had joined the guerrillas and they were very active in
that area. The guerrillas there knew him by name, knew he was a
member of the police, and had threatened him personally while he
was a member of the national police. He stated that the govern-
ment was unable to protect him in El Salvador and he had fled to
avoid being killed. The respondent additionally testified that two of
his relatives, who had been "local commanders," had committed
suicide because of their fear of the guerrillas.
  In addition to his own testimony, the respondent presented two
witnesses who had known him in El Salvador. They testified that
the situation in his hometown was very dangerous; that it was an
area of ongoing fighting between the military and the guerrillas;
that the guerrillas there killed people for "having been" in the
military; that the guerrillas knew of the respondent's past service;
that he would be plinighed or "disappear" if he returned to his
hometown even if he was no longer in service; and that the govern-
ment could not protect him. One of the two witnesses also stated
that the guerrillas had the names of the people who had been in
the service and would immediately find out if the respondent re-
turned to his hometown.
  An alien who is seeking withholding of deportation from any
country must show that his "life or freedom would be threatened
Interim Decision #3065

in such country on account of race, religion, nationality, member-
ship in a particular social group, or political opinion." Section
243(h)(1) of the Immigration and Nationality Act, 8 U.S.C.
§ 1253(h)(1) (1982). In order to make this showing, the alien must
establish a "clear probability" of persecution on account of one of
the enumerated grounds. INS v. Stevie, 467 U.S. 407 (1984). This
clear probability standard requires a showing that it is more likely
than not that an alien would be subject to persecution. Id. at 429-
30.
   In order to establish eligibility for a grant of asylum, an alien
must demonstrate that he is unwilling or unable to return to his
country because of persecution or a "well-founded fear" of persecu-
tion on account of race, religion, nationality, membership in a par-
ticular social group, or political opinion. Section 208 of the Act, 8
U.S.C. § 1158 (1982). The Board previously took the position that, as
a practical matter, the showing required to establish a well-found-
ed fear of persecution for asylum purposes was the same as that
required to establish a clear probability of persecution for purposes
of withholding of deportation. Matter of _Acosta, 19 I&N Dec. 211
(BIA 1985). The Supreme Court has rejected this approach in INS
v. Cardona Fonseca, 420 U.S. 421 (1987). In that case, the Court
found it reasonable to assume that Congress intended to make it
more difficult to establish absolute entitlement to withholding of
deportation under section 243(h) than to establish mere eligibility
for asylum under section 208 of the Act. Id. at 443-44. In Matter of
Mogharrabi, 19 I&N Dec. 439 BIA 1987), the Board reexamined the
burden of proof in asylum cases in light of the Supreme Court's
holding. In that case, it was held that an applicant for asylum has
established a well-founded fear if a reasonable person in his cir-
cumstances would fear persecution on account of one of the
grounds specified in the Act. We noted that a reasonable person
may fear persecution even where its likelihood is significantly less
than clearly probable. In considering asylum claims, an alien's own
testimony may be sufficient, without corroborative evidence, to
prove a well-founded fear of persecution where that testimony is
believable, consistent, and sufficiently detailed to provide a plausi-
ble and coherent account of the basis for his fear.
  Based upon our review of the record, we fmd that the respondent
has failed to demonstrate his eligibility for asylum and, conse-
quently, also has not satisfied the higher burden of proof necessary
to establish eligibility for withholding of deportation.
  There are two related, but distinct, bases underlying this re-
spondent's asylum claim. The first is his fear arising from the
events that occurred while he was a policeman and guard in El Sal-
                                  can
                                              Interim Decision #3065

vador prior to his departure in 1982. The second aspect of his claim
is the fear that he will face persecution as a former national police-
man if he returns to El Salvador.
   We do not find that the respondent can demonstrate a well-
founded fear of persecution "on account of one of the grounds
specified in the Act based on the events that occurred while he was
a policeman and guard in El Salvador from 1967 to 1982. In so
holding, we find that dangers faced by policemen as a result of that
status alone are not ones faced on account of race, religion, nation-
ality, membership in a particular social group, or political opinion.
   There is presently a political struggle ongoing in El Salvador, the
ultimate objective of which is supremacy of one side over the other.
The guerrillas, whom the respondent fears, appear intent on over-
throwing the government. The government's obvious intent is to
thwart the guerrillas' objectives. Unfortunately, violence appears
inherent to such revolutionary struggles. Guerrillas often engage
in violence, not only against military targets, but also against civil-
ian institutions that, whether intentionally or not, support domes-
tic stability and the strength of the existing government. Police-
men are by their very nature public servants who embody the au-
thority of the state. As policemen around the world have found,
they are often attacked either because they are (or are viewed as)
extensions of the government's military forces or simply because
they are highly visible embodiments of the power of the state. In
such circumstances, the dangers the police face are no more related
to their personal characteristics or political beliefs than are the
dangers faced by military combatants. Such dangers are perils aris-
ing from the nature of their employment and domestic unrest
rather than "on account of immutable characteristics or beliefs
within the scope of sections 101(a)(42)(A) or 243(h) of the Act, 8
U.S.C. §§ 1101(a)(42)(A) and 1253(h) (1982). Accordingly, we do not
find that the respondent has demonstrated a well-founded fear of
persecution "on account of one of the grounds protected by the
Act by virtue of the attacks and dangers he faced as a policeman
and guard in El Salvador prior to his departure in 1982.
   We note that if one were to find that a policeman or guerrilla
was a victim of "persecution" within the scope of the Act based
solely on the fact of an attack by one against the other, then it
would follow that the attacker had participated in an act of "perse-
cution" that would forever bar him or her from relief under sec-
tions 208(a) or 243(h). Such a "broad" interpretation of the concept
of persecution "on account of race, religion, nationality, member-
ship in a particular social group, or political opinion" would have
the actual effect of greatly narrowing the group of persons eligible
Interim Decision #3065

for asylum and withholding. Virtually all participants on either
side of an armed struggle could be characterized as "persecutors"
and would thereby be ineligible for asylum or withholding of depor-
tation. The concept of "persecution" has not been so broadly de-
fined.
   The second aspect of the respondent's claim is his fear arising
from his status as a former member of the national police. This is
in fact an immutable characteristic, as it is one beyond the capac-
ity of the respondent to change. It is possible that mistreatment oc-
curring because of such a status in appropriate circumstances
could be found to be persecution on account of political opinion or
membership in a particular social group. For example, where hos-
tilities have ceased, an asylum applicant who is subject to mistreat-
ment because of a past association may be able to demonstrate a
well-founded fear of persecution on account of a protected ground.
We note that an applicant does not bear the unreason-
able burden of establishing the exact motivation of a "persecutor"
where different reasons for actions are possible. However, an appli-
cant does bear the burden of establishing facts on which a reasona-
ble person would fear that the danger arises on account of his race,
religion, nationality, membership in a particular social group, or
political opinion. The Government may also introduce supporting
or contradictory evidence regarding both the potential for mistreat-
ment and the reasons therefor.
  In this ease, the facts surrounding the possible danger faced by
the respondent if he returns to his hometown and, more specifical-
ly, the reasons for that danger are not clearly developed. Although
the respondent testified that he fears harm if he returns to El Sal-
vador, his testimony relates to events that occurred while he was
an active member of the government forces prior to his departure
from El Salvador. One of his witnesses stated that the respondent
would face danger if he returned to his hometown but was unable
to testify to any instances of individuals endangered for having
been in the military service. The final witness, however, did testify
that the guerrillas in the respondent's hometown knew of those
"who served in the military" and the respondent would "disap-
pear" if he returned. But this witness also testified that the town
was in a situation of strife between the army and the guerrillas
with "terrible" fighting ongoing.
  On this record, we do not find that the respondent has adequate-
ly demonstrated a well founded fear of "persecution" on account of
                       -


his status as a former policeman; rather, the record would indicate
a danger that one with ties to a participant in a violent struggle
might expect if he ventures into an area of open conflict. We note
                                cao
                                             Interim Decision #3065

that participants in an ongoing armed struggle may well have rea-
sons for refusing to tolerate the presence of "past" opponents in
territories under their control or under dispute, unrelated to perse-
cution on account of a protected status (eg, the most fundamental
question of whether or not such individuals are in fact no longer
taking part in the hostilities either overtly or covertly).
   Even if one assumes the respondent's claim in this respect has
been otherwise demonstrated, however, we do not find an asylum
claim based on nongovernmental action adequately established
where the evidence the respondent presents is directed to so local
an area of his country of nationality. Although the respondent ex-
pressed a general fear of returning to El Salvador, his specific evi-
dence focuses on the danger he would face if he returned to his
hometown, where he is known by guerrillas and the conflict is still
ongoing. The record in fact indicates that the respondent resided in
San Salvador for 2 years prior to his departure from El Salvador
and only visited his mother on weekends at his hometown when he
had permission.
   Because we do not find that the respondent has demonstrated his
eligibility for the requested relief from deportation, the appeal will
be dismissed.
   ORDER: The appeal is dismissed.
   FURTHER ORDER: Pursuant to the immigration judge's
order and in accordance with our decision in Matter of Chouliaris,
16 I&N Dec. 168 (BIA 1977), the respondent is permitted to depart
from the United States voluntarily within 30 days from the date of
this order or any extension beyond that time as may be granted by
the district director; and in the event of failure so to depart, the
respondent shall be deported as provided in the immigration
judge's order.""")

# Case 12
add_case("""Jianli Chen v. Holder
Court of Appeals for the First Circuit

Citations: 703 F.3d 17, 2012 WL 6700588
Docket Number: 11-1925, 12-1250
Judges: Lynch, Selya, Stahl
Opinion
Authorities (25)
Cited By (59)
Summaries (7)
Similar Cases (21.2K)
PDF
Headmatter
JIANLI CHEN, Petitioner, v. Eric H. HOLDER, Jr., Attorney General, Respondent. Jianli Chen and Min Fen Hu, Petitioners, Eric H. Holder, Jr., Attorney General, Respondent.
Nos. 11-1925, 12-1250.

United States Court of Appeals, First Circuit.

Dec. 21, 2012.

*19 Gang Zhou on brief for petitioners.

Tony West, Assistant Attorney General, Civil Division, Stuart F. Delery, Acting Assistant Attorney General, Richard M. Evans, Assistant Director, Office of Immigration Litigation, and Kevin J. Conway, Attorney, on brief for respondent.

Before LYNCH, Chief Judge, SELYA and STAHL, Circuit Judges.
Combined Opinion by Selya
SELYA, Circuit Judge.
The petitioners, Jianli Chen and her husband, Min Fen Hu, are Chinese nationals. They seek judicial review of the final orders of the Board of Immigration Appeals (BIA) (i) affirming the denial of their applications for asylum, withholding of removal, and relief under the United Nations Convention Against Torture (CAT); and (ii) denying their motion for reconsideration. Chen appears both as an applicant for relief in her own right and as a derivative beneficiary of her husband's application. After careful consideration, we leave the BIA's orders intact.

I. BACKGROUND

Hu entered the United States without inspection on December 1, 2005. Chen followed suit on March 8, 2006. Federal authorities subsequently placed them in removal proceedings. See 8 U.S.C. §§ 1182(a)(6)(A)(i), 1229a(a)(2). Both petitioners conceded removability and cross-applied for asylum, withholding of removal, and CAT relief. Their cases were consolidated for hearing before an immigration judge (IJ).

We rehearse the facts in line with the petitioners' direct testimony. Chen and Hu were married in China on November 14, 2001. On January 13, 2003, Chen gave *20 birth to their first child (a daughter). Approximately two months later, government functionaries directed the implantation of an intrauterine device (IUD) in Chen, pursuant to China's coercive population control policy.

Chen and Hu went through a sham divorce in order to avoid the annual pregnancy checks required for all married women. Chen then asked a private physician to remove the IUD so that she could bear a second child. She became pregnant and, to conceal her condition from the authorities, she hid at her uncle's home. Despite this professed need for secrecy, the petitioners traveled openly to Thailand for a vacation, securing visas and passing through customs.

During this pregnancy, Chen skipped the mandatory gynecological examinations routinely scheduled by the municipal family planning office. Nevertheless, she voluntarily underwent two ultrasound examinations, including one at a provincial hospital run by the Chinese government.

When family planning officials concluded that Chen was trying to dodge the population control policy, they took her mother into custody and Chen was informed that her mother would be held indefinitely unless Chen allowed a pregnancy check to be performed. Chen capitulated: on August 23, 2005 (shortly after returning from the Thailand vacation), she was examined, found to be pregnant, and subjected to a forced abortion.

In mid-October, Hu left China. He flew from Beijing to Paris and then traveled to Venezuela, where he remained for three days. Thereafter, he spent two months traveling to the United States by boat, vehicle, and on foot. Almost immediately after his arrival, the Department of Homeland Security commenced removal proceedings against him in the New York immigration court.

Chen left China three days after Hu. She remained in Venezuela for five months before traveling to the United States through Mexico. She arrived in March of 2006 and, in short order, removal proceedings were instituted against her.

On May 17, 2006, the petitioners remarried in the United States. Roughly two- and-one-half years later, Chen gave birth to a second child (a son) in New York.

In the removal proceedings, the petitioners conceded the foundational factual allegations but insisted that, if repatriated, they would be subjected to involuntary sterilization. When they moved to Springfield, Massachusetts, the cases were transferred to Boston.

Following an evidentiary hearing, the IJ determined that the petitioners' testimony was not believable and that, therefore, their factual account could not be credited. With these determinations in mind, the IJ concluded that the petitioners had failed to establish either past persecution or a well-founded fear of future persecution. Consequently, she rejected the petitioners' cross-applications for relief and ordered them removed to China.

The petitioners appealed to the BIA, which upheld the IJ's adverse credibility determinations and affirmed the IJ's rulings save for a perceived need to remand Hu's asylum application for findings as to whether he suffered past persecution. The petitioners moved for reconsideration, arguing that the BIA had improvidently fashioned its own factual findings in order to uphold the adverse credibility determinations. The BIA rebuffed this argument, stating that its prior decision did not "incorporate[ ] or rel[y] ... on any improper factfinding."

In the same motion, the petitioners sought reconsideration of the remand or *21 der. The BIA reconsidered this issue and withdrew the remand order, accepting Hu's representation that he did not wish to pursue the issue of past persecution.

The petitioners have now sought judicial review. 1 We have jurisdiction under 8 U.S.C. § 1252(a)(1).

II. ANALYSIS

Our analysis necessarily begins with the standard of review, which is complicated here because the petitioners have challenged both the BIA's original decision and its partial denial of their motion for reconsideration. Withal, the issues are essentially the same and, for ease in exposition, we assume, without deciding, that the more petitioner-friendly substantial evidence standard applies to those issues. 2

The substantial evidence standard pertains to the review of factual findings, including credibility determinations. Segran v. Mukasey, 511 F.3d 1, 5 (1st Cir. 2007). Viewing the evidence through this deferential lens, we will reverse only if the record is such as to compel a reasonable factfinder to reach a contrary determination. Pan v. Gonzales, 489 F.3d 80, 85 (1st Cir.2007). In other words, findings of fact will stand as long as they are "supported by reasonable, substantial, and probative evidence on the record considered as a whole." INS v. Elias-Zacarias, 502 U.S. 478, 481, 112 S.Ct. 812, 117 L.Ed.2d 38 (1992) (internal quotation marks omitted).

Rulings of law are a different matter. Such rulings engender de novo review, but with some deference to the agency's reasonable interpretation of statutes and regulations that fall within its sphere of authority. See Seng v. Holder, 584 F.3d 13, 17 (1st Cir.2009); see also Chevron U.S.A., Inc. v. Natural Res. Def. Council, Inc., 467 U.S. 837, 843-44, 104 S.Ct. 2778, 81 L.Ed.2d 694 (1984).

In the immigration context, judicial review ordinarily focuses on the BIA's decision. See, e.g., Seng, 584 F.3d at 17. But where, as here, the BIA adopts portions of the IJ's findings while adding its own gloss, we review both the IJ's and the BIA's decisions as a unit. Villa-Londono v. Holder, 600 F.3d 21, 23 (1st Cir.2010).

To qualify for asylum, an alien must establish that he is a refugee within the meaning of 8 U.S.C. § 1101(a)(42). Carrying this burden requires a showing of either past persecution or a well-founded fear of future persecution. See id. § 1101(a)(42)(A); see also Rivas-Mira v. Holder, 556 F.3d 1, 4 (1st Cir.2009).

The immigration statutes take special account of persons who are forced to flee their homeland because of coercive family planning policies. The law provides in pertinent part that the term "refugee" shall include "a person who has been forced" through government action "to abort a pregnancy or to undergo involuntary sterilization." 8 U.S.C. § 1101(a)(42)(B).

An asylum-seeker's testimony alone, if credible, may suffice to carry the burden of establishing refugee status. See Bebri v. Mukasey, 545 F.3d 47, 50 (1st Cir.2008). But the factfinder need not take an asylum-seeker's testimony at face *22 value; rather, the factfinder may discount such testimony, or disregard it entirely, if she reasonably deems it to be "speculative or unworthy of credence." Id.

Against this backdrop, we turn to the case at hand. There is no question that the petitioners' account, if true in all its particulars, could support a claim for asylum. The problem is that the factfinder— the IJ — did not believe the petitioners' story; and if that story is set to one side, the record contains no basis for granting asylum. Thus, our inquiry focuses on the propriety of the adverse credibility determinations.

Before undertaking this inquiry, we pause to note that the IJ's adverse credibility determinations are governed by the provisions of the REAL ID Act, Pub.L. No. 109-18, 119 Stat. 302 (2005), codified at 8 U.S.C. § 1158(b)(1)(B)(iii). This statute provides that a factfinder

may base a credibility determination on the demeanor, candor, or responsiveness of the applicant or witness, the inherent plausibility of the applicant's or witness's account, the consistency between the applicant's or witness's written and oral statements (whenever made and whether or not under oath, and considering the circumstances under which the statements were made), the internal consistency of each such statement, the consistency of such statements with other evidence of record (including the reports of the Department of State on country conditions), and any inaccuracies or falsehoods in such statements, without regard to whether an inconsistency, inaccuracy, or falsehood goes to the heart of the applicant's claim, or any other relevant factor.
8 U.S.C. § 1158(b)(l)(B)(iii). 3 We proceed to evaluate the adverse credibility determinations under these guidelines and in light of the totality of the circumstances. See Rivas-Mira, 556 F.3d at 4.

The petitioners advance two broad claims of error with respect to the denial of asylum. Them first attack is procedural; it posits that the BIA engaged in improper factfinding to sustain the adverse credibility determinations. Their second attack is substantive; it posits that both the IJ and the BIA arbitrarily denigrated their testimony and, thus, erred in rejecting their claims for asylum based on a well-founded fear of future persecution. We examine these challenges sequentially. We then address some miscellaneous matters.

A. The Procedural Claim.

To place into perspective the petitioners' argument that the BIA overstepped its bounds by engaging in independent factfinding, it is necessary to understand the relative roles of the IJ and the BIA in the decisional process. The IJ has the front-line duty of finding the facts. Her factual findings, including credibility determinations, are reviewed by the BIA only to ensure that they are not clearly erroneous. See 8 C.F.R. § 1003.1(d)(3)(i). Although the BIA may take "administrative notice of commonly known facts such as current events or the contents of official documents," it is prohibited from "engag[ing] in factfinding in the course of deciding appeals." Id. § 1003.1(d)(3)(iv). The petitioners say that, in this instance, the BIA usurped the role of the IJ.

*23 At the outset, the petitioners take issue with the BIA's statement that the IJ found their testimony "internally inconsistent." The IJ, they say, never made any finding of internal inconsistency. This hair-splitting is unpersuasive. Although the IJ did not use the phrase "internally inconsistent" to describe the petitioners' testimony, her findings justify the use of that description. In her analysis, the IJ refers to "diverging answers," "discrepancy," and "dissonance" in the petitioners' testimony. These findings fit comfortably under the carapace of internal inconsistency. Let us be perfectly clear. Although the BIA may not engage in independent factfinding, it has the prerogative—indeed, the duty—of examining the basis for, and then synthesizing and analyzing, the IJ's findings. See Rotinsulu v. Mukasey, 515 F.3d 68, 73 (1st Cir.2008). This multifaceted role is not meant to be robotic. The BIA is not bound simply to parrot the precise language used by the IJ but, rather, may use its own vocabulary. In pursuing this claim of procedural error, the petitioners also assail the BIA's statement that Hu's credibility was suspect because he denied that he was ever questioned by border patrol agents. The premise of the petitioners' attack is the assumption that the BIA could not reasonably rely on Hu's 1-213 form because that form does not indicate on its face whether a Chinese-language interpreter capable of a dialect understandable to Hu was provided. 4 We reject this contention. Strict rules of evidence do not apply in immigration proceedings. See Henry v. INS, 74 F.3d 1, 6 (1st Cir.1996). It is normally enough if the IJ reasonably finds a proffered piece of evidence to be reliable and its use to be fundamentally fair. See Yongo v. INS, 355 F.3d 27, 30 (1st Cir.2004). The 1-213 form at issue here satisfies these criteria, and the IJ found as much. At the hearing before the IJ, Hu at first denied speaking to the border patrol agents at all. He then retreated to the position that he had answered only a few routine questions. The IJ credited the I-213 form, stating that it was "sufficiently reliable on [its] face" and "was compiled with the aid of a telephonic interpreter." These findings are supported by the record. Relatedly, the petitioners maintain that the BIA improperly supplemented the IJ's findings with respect to the likelihood of forced sterilization in China. Specifically, they point to the BIA's statement that they "have not shown that having two children born almost six years apart violates their village's family planning policy." They overlook, however, that this statement is followed by a citation to a designated portion of the IJ's decision and is simply a paraphrasing of the IJ's language. For these reasons, the petitioners' procedural claim fails. Simply put, the BIA did not engage in independent factfinding. B. The Substantive Claim. We turn next to the petitioners' substantive claim of error, which frontally challenges the adverse credibility determinations. The petitioners start by questioning the agency's reliance on omissions from their testimony. They insist that they were entitled to, but did not receive, an opportunity to explain any supposed *24 omissions. Cf. Zeru v. Gonzales, 503 F.3d 59, 69-70 (1st Cir.2007) ("An IJ's credibility determinations demand deference where (1) the discrepancies and omissions described by the IJ are actually present in the record; (2) those discrepancies and omissions provide specific and cogent reasons to conclude that the petitioners provided incredible testimony regarding facts central to the merits of the asylum claim; and (3) petitioners do not provide a convincing explanation for the discrepancies and omissions.").
This argument is jejune. The petitioners have had multiple opportunities, such as in their briefing to the BIA and to this court, to explain the omissions. Despite these multiple opportunities, the explanations that they have advanced are unconvincing.

This brings us to the petitioners' central theme: that the adverse credibility determinations are clearly erroneous. The critical question, of course, is whether those determinations are supported by substantial evidence in the record as a whole. See Pan, 489 F.3d at 85. We answer this question affirmatively.

A trial judge sees and hears the witnesses at first hand and is in a unique position to evaluate their credibility. In the absence of special circumstances — not present here — reviewing courts ordinarily should defer to such on-the-spot judgments. See, e.g., Ang v. Gonzales, 430 F.3d 50, 57 (1st Cir.2005); Aguilar-Solis v. INS, 168 F.3d 565, 570-71 (1st Cir.1999). This is especially true when, as in this case, the trial judge fortifies her findings with particularized observations as to demeanor and examples of inconsistencies and implausibilities. See Olujoke v. Gonzales, 411 F.3d 16, 21-22 (1st Cir.2005); Laurent v. Ashcroft, 359 F.3d 59, 64 (1st Cir.2004). We illustrate briefly.

Here, the IJ observed that both petitioners were "evasive and equivocal during certain crucial portions of their testimony;" that both "testified in a furtive and incomplete manner when asked about their infiltration into the United States;" and that both "were non-responsive to important queries." Chen, in particular, "appeared to stonewall the fact-finding process." Although it is difficult to assess demeanor-based findings from a paper record, we discern nothing in the hearing transcript that undercuts the IJ's detailed observations.

The IJ also identified a litany of inconsistencies and implausibilities in the petitioners' tale. For example, Chen testified that she hid at her uncle's house in order to elude detection by Chinese government officials, yet she proceeded to leave this safe haven to take an eight-day vacation with Hu in Thailand. Further, the IJ remarked Chen's "opaque and inconsistent" testimony as to why she scheduled an ultrasound examination at a government-run hospital instead of an available private facility. 5

The IJ had obvious difficulty in swallowing Chen's testimony about her forced abortion. Chen originally testified inconsistently as to whether the abortion was or was not performed on the same day that a pregnancy check revealed her gravidity (August 23, 2005). The IJ reasonably concluded that a discrepancy relating to so central a fact was telling.

*25 Similar inconsistencies plagued Chen's description of the logistics of her entry into the United States. She testified at one point that she agreed to pay a smuggler $70,000, giving him $1,000 and promising to pay the balance from her earnings in the United States. She subsequently testified, however, that Hu's father sold one of his homes in China to pay the smuggler's fee. Although the petitioners have attempted to provide an explanation for this discrepancy, the IJ concluded that these "starkly different answers" were irreconcilable, and we cannot say that the evidence would compel a reasonable fact-finder to reach a contrary conclusion.

The IJ identified comparable inconsistencies and implausibilities in Hu's testimony, particularly with respect to his entrance into the United States and his subsequent apprehension. For example, when asked if border patroi agents interviewed him on December 2, 2005, Hu initially claimed that the agents had not asked him any questions. Later on, he backtracked, stating that the agents had only asked him about his parents, his geographic origins, and his age. The IJ reasonably concluded that both of these answers were false. As she pointed out, the veracity of this account was called into serious question by the broader range of information contained in his I-213 form.

This is part of a larger picture. The IJ's doubts about the petitioners' credibility were compounded by a painstaking comparison of their hearing testimony with both their written applications for asylum and their 1-213 forms. The IJ compiled a long list of such discrepancies. We offer a sampling.

• Despite their hearing testimony, neither Hu nor Chen asserted in their I-213 forms that they had any children.
• Chen's asylum application and hearing testimony were materially inconsistent as to when she learned of China's one-child policy.
• Chen's asylum application states that on one occasion family planning officials came to her parents' home and questioned her mother about Chen's whereabouts and, on another occasion, barged into her parents' house to search for her. Chen's testimony before the IJ did not mention either of these alleged incidents.
• Chen's 1-213 form memorializes that she told the border patrol agents that she entered the United States to seek employment and did not fear returning to China. She testified, however, that she came to the United States to escape China's coercive population control policy and that she feared returning there.
The record contains other inconsistencies as well. For instance, Hu's testimony during the hearing as to the route he took in journeying from China to the United States did not match the description of his journey contained in his 1-213 form (omitting, among other things, any mention of his stop in Cuba).

To cinch matters, the record is pockmarked with implausibilities. For example, the petitioners never satisfactorily explained why they would opt for a holiday in Thailand, risking official scrutiny, if Chen was hiding from the government. By like token, they never satisfactorily explained either Chen's decision to use a government-run hospital instead of an available private facility or why they traveled separately to reach the United States and took different routes in doing so. The IJ was entitled to give weight to the absence of plausible explanations. See, e.g., Bebri, 545 F.3d at 49; Aguilar-Solis, 168 F.3d at 571.

*26 While some of the discrepancies identified by the IJ may be picayune if viewed in isolation, the record as a whole presents a picture consistent with the IJ's adverse credibility determinations. Fairly viewed, this may well be a situation in which the whole is greater than the sum of its parts. See Pan, 489 F.3d at 86 (explaining that even though inconsistencies "may seem like small potatoes," their cumulative effect may be great); cf. Bourjaily v. United States, 483 U.S. 171, 179-80, 107 S.Ct. 2775, 97 L.Ed.2d 144 (1987) (acknowledging that the "sum of an evidentiary presentation may well be greater than its constituent parts"). In the last analysis, it is for the IJ, not this court, to decide whether omissions are significant, whether inconsistencies are telling, and whether implausibilities should be accorded decretory significance. See Kho v. Keisler, 505 F.3d 50, 56 (1st Cir.2007) (explaining that "[t]he court reviews agency proceedings but does not act as a finder of fact itself').

The petitioners further complain that the agency relied on unfavorable portions of documentary exhibits, including the 2007 U.S. Department of State Country Report on Human Rights Practices in China and the Lianjiang County Family-Planning Information Promotion Q & A for General Public. As the petitioners see it, the agency should have focused on more favorable reports or, at least, on more favorable passages from the cited reports.

This plaint is unfounded. Just as a factfinder may sift through conflicting testimony, accepting some testimony and rejecting other testimony, so too may a factfinder sift through relevant documents, determining which documents are persuasive and which statements within a particular document should be given weight. See Pan, 489 F.3d at 87 & n. 6 (citing Martinez v. INS, 970 F.2d 973, 975 (1st Cir.1992)). In such matters, a court must defer to the factfinder's reasonable choices.

There is one loose end. The petitioners seem to suggest, albeit obliquely, that the agency erred in concluding that they had not established a well-founded fear of persecution based on the birth of their second child in the United States. This suggestion lacks force. As the Second Circuit explained, the BIA

has declined to construe the statutory term "refugee" to exclude or to include all Chinese nationals who have fathered or given birth to more than one child. Rather, it has determined that a case-by-case review is necessary to identify which Chinese nationals with two or more children demonstrate a fear of future persecution that is both subjectively genuine and objectively reasonable.
Shao v. Mukasey, 546 F.3d 138, 142 (2d Cir.2008).

In this instance, documentary evidence cited by the IJ contradicts the claim of a well-founded fear of persecution based on the birth of the petitioners' second child in the United States. For example, the IJ supportably relied on the 2007 U.S. Department of State China Profile of Asylum Claims and Country Conditions ¶ 112, which states in pertinent part that, with respect to the petitioners' home province, "children born abroad ... are not considered as permanent residents of China, and therefore are not counted against the number of children allowed under China's family planning law." Here, too, the burden of persuasion was on the petitioners, and the record as a whole does not compel a contrary conclusion.

We have said enough about the asylum claims. Given the myriad inconsistencies in the petitioners' testimony, the implausibilities inherent in their account, their failure to offer convincing explanations of *27 seeming contradictions, and the IJ's detailed demeanor-related observations, we hold that the adverse credibility determinations are supported by substantial evidence. This holding, in turn, defeats the asylum claims. Stripped of the petitioners' undependable testimony, the record contains no evidence sufficient to ground the petitioners' professed fear of future persecution: a factfinder cannot reliably tell what really happened in China before the petitioners fled, nor can a factfinder reliably forecast what may await them upon their repatriation. The petitioners have the burden of proof and, on this scumbled record, we cannot say that the agency erred in concluding that they failed to carry it.

C. Other Relief.

We need not linger long over the petitioners' claims for withholding of removal. Claims for asylum and claims for withholding of removal have similar elements, but the quantum of proof required for the latter is more demanding. Compare 8 U.S.C. § 1101(a)(42)(A) and id. § 1158(b), with id. § 1231(b)(8) and 8 C.F.R. § 208.16(b). Thus, an alien who cannot establish the elements of an asylum claim cannot prevail on a counterpart claim for withholding of removal. See Ying Jin Lin v. Holder, 561 F.3d 68, 74 (1st Cir. 2009); Segran, 511 F.3d at 7. That principle applies here.

This leaves the petitioners' CAT claims. It is settled beyond hope of contradiction that claims perfunctorily advanced in skeletal fashion are deemed abandoned. See, e.g., Jiang v. Gonzales, 474 F.3d 25, 32 (1st Cir.2007); United States v. Zannino, 895 F.2d 1, 17 (1st Cir.1990). Because the petitioners have offered no developed argumentation in support of their CAT claims, we reject them out of hand.

III. CONCLUSION

We need go no further. The petitions for judicial review are denied.

So Ordered.""")

# Case 13
add_case("""Ivanov v. Holder, Jr.
Court of Appeals for the First Circuit

Citations: 736 F.3d 5, 2013 WL 6037164, 2013 U.S. App. LEXIS 23115
Docket Number: 11-1814
Judges: Torruella, Thompson, Kayatta
Opinion
Authorities (32)
Cited By (42)
Summaries (14)
Similar Cases (191)
PDF
Headmatter
Pavel IVANOV; Irina Kozochkina, Petitioners, v. Eric H. HOLDER, Jr., Attorney General, Respondent.

No. 11-1814.

United States Court of Appeals, First Circuit.

Nov. 15, 2013.

*7 Randy Olen, with whom Robert D. Watt, Jr. was on brief, for petitioners.

Andrew Nathan O'Malley, with whom Stuart F. Delery, Acting Assistant Attorney General, Civil Division, Ernesto H. Molina, Jr., Assistant Director, Office of Immigration Litigation, and D. Nicholas Harling, Attorney, Office of Immigration Litigation, were on brief, for respondent.

Before TORRUELLA, THOMPSON, and KAYATTA, Circuit Judges.
Lead Opinion by Thompson
*8THOMPSON, Circuit Judge.
Petitioners Pavel Ivanov and Irina Ko-zochkina seek review of a final order of removal. They say the immigration courts erred by finding that the persecution Iva-nov experienced in Russia was not "on account of' his Pentecostal faith. We agree. After careful consideration of the decision and the record, we vacate and remand for additional proceedings.

Facts and Procedural History

Petitioners are natives and citizens of Russia. Ivanov is a long-standing member of the Pentecostal Church, which Kozochk-ina, a Baptist, now attends.1

Petitioners entered the United States in May 2003 on five-month educational exchange visas.2 Having heard from family and fellow Pentecostals in Russia of ongoing threats and violence against persons of their faith, Petitioners overstayed their visas and applied for asylum, withholding of removal, and relief under the Convention Against Torture (CAT) in September 2004.3 Petitioners were married in Newport, Rhode Island in October 2004.

In August 2005, the Department of Homeland Security (DHS) served Petitioners with Notices to Appear, charging them with removability under the Immigration and Nationality Act. See 8 U.S.C. § 1227(a)(1)(B). Petitioners filed amended applications for asylum, withholding of removal, and CAT relief in June 2007. They appeared before an Immigration Judge (IJ) in a series of hearings between 2006 and 2009. Because the IJ found Ivanov credible, we recount the facts here as Iva-nov presented them in his documentation and testimony.

Ivanov was born in Chelyabinsk, Russia on November 21,1983. His parents raised him in the Pentecostal faith, practicing in secret during the anti-religious Soviet regime, then joining a church in 1995 as Russia began to open up to religion after the fall of communism.

Pentecostals represent a religious minority in Russia.4 Though the Russian Constitution provides for freedom of religion, "[mjany citizens firmly believe that adherence to the Russian Orthodox Church ... is at the heart of their national identity,"5 and "members of minority and 'non-traditional' religions," including Pentecostals, "continue to encounter prejudice, societal discrimination, and in some cases physical attacks."6 Local authorities reportedly do not adequately respond *9to such attacks.7 For example, prior to 2005, Evangelicals and Pentecostals in various regions reported the vandalizing and burning of prayer houses, including in Iva-nov's hometown of Chelyabinsk, where authorities made no arrests.8

Ivanov's memories of problems for his church date back to March 1996, when he learned that members of the Russian Orthodox Church intercepted Pentecostal literature sent from France. Then, on January 7, 1997 (Orthodox Christmas), he heard that a group of "Barkashovtsy"— Russian nationalist, neo-Nazi "skinheads"9 —had burned his church's office and beat up the night watchman. Later, on May 30, 1999, while Ivanov and his parents were visiting their pastor's home for Pentecost, a mob led by a disgraced Russian Orthodox priest attacked the home, beating the pastor's wife, looting the premises, and burning religious literature.

Ivanov testified that he was personally mistreated because of his religious beliefs on several occasions. First, on November 21, 1999, during Ivanov's baptism into the Pentecostal faith on his sixteenth birthday, bystanders heckled and threw bottles at celebrants during the initial ceremony at a public pool. That evening, while rites continued at the prayer house, skinheads burst in, shot rubber bullets, confiscated literature, and ransacked the house.

Second, on April 20, 2002, the anniversary of Hitler's birth, skinheads attacked Ivanov as he left the church-run drug rehabilitation center where he volunteered.10 His church operated the center as part of its mission of public service. Patients received medical treatment and followed a strict regimen of daily bible study.

That night, as Ivanov left the center, four young skinheads "knocked [him] down and dragged [him] 3 blocks" to a basement where he was "chained and beaten with full plastic water bottles." They ■ handcuffed him, then-applied an electric shock to one hand and put cigarettes out on the other. They told him he had two days to figure out how to close the' church's " 'satanic' dispensary." The skinheads then left Ivanov for nearly three ' days without food and water. His parents filed a police report, but to their knowledge no action was taken. Fortunately, the skinheads released Ivanov of their own accord a few days later. It was only after Iva-nov's. release that he realized the drug rehabilitation center's work interfered with the skinheads' lucrative drug trade.

Third, in February 2003, Ivanov "was summoned to the local police department." There, a federal security service officer identified as Major Kozlov ordered Ivanov to provide false testimony in the prosecution of his pastor. Prosecutors accused *10the pastor of using hypnosis to extort a ten-percent tithe from congregants. Major Kozlov told Ivanov he "would be sorry for not cooperating" with the prosecution.

A few days later, in early March 2003, four skinheads attacked Ivanov in the lobby of his apartment building. They beat him with batons while wearing rubber gloves, bruising his legs so severely that he missed school for a week. Although they wore no uniforms, Ivanov knew they were skinheads by the weapons they used. Because the beating occurred shortly after Ivanov's conversation with Major Kozlov, Ivanov believes the skinheads were retaliating against him for his refusal to testify against his pastor. Ivanov called the police when he got back to his apartment, but no one ever came. Ivanov did not seek further police assistance or medical attention because he thought it would be futile.

Fourth, on April 22, 2003, unknown assailants threw Molotov cocktails at Iva-nov's home in the middle of the night. Ivanov, his father, and his mother were home. Fortunately, Ivanov's mother was awake and the family was able to put out the resulting fire. That same night, the church's drug rehabilitation center also was set on fire. Ivanov did not see the people who threw the Molotov cocktails, but based on the perpetrators' precision and the familiar timing of the attacks— almost exactly one year after skinheads accosted him as he left the center and just two days after "Hitler's Birthday" — he believes the skinheads were again responsible. Petitioners left Russia and came to the United States roughly one month after this incident.

In his asylum application, Ivanov stated that he feared if he returned to Russia, skinheads would "sever[e]ly harm[] or kill[ ]" him, or the federal security service would imprison him on "trumped-up" charges or confine him to a mental facility under a false diagnosis, because of his membership in a "non-traditional" sect and his refusal to testify falsely against his pastor. At a hearing before the IJ in July 2007, after recounting his past mistreatment, Ivanov said he feared if he returned to Russia, "the same thing would [happen]." He also said he would "continue to be [subject] to the same lawlessness that [he] felt before."

When Ivanov's attorney asked if he had any fear of the government, Ivanov explained that it was "a well-known and established fact that ... the skinheads ... are connected to the government structure." He elaborated that because he "look[ed] like [a] Russian" and his religious beliefs were not outwardly apparent, the only way the "young kids" who attacked him would know that he did not fit then-view of a "pure nation [or] pure race in Russia" is by the guidance or influence of "somebody from above."

In July 2009, the IJ delivered an oral decision denying Petitioners relief. Although the IJ found Ivanov's testimony to be credible and generally consistent, he determined that Ivanov "fell short of credibility" where he drew "conclusions ... from the facts" and engaged in "speculation ... with regard to the abusive activity of the skinheads." Accepting for the sake of discussion that Ivanov's experiences amounted to past persecution, the IJ dismissed Ivanov's assertion that the skinheads were connected to government authorities as mere supposition without record support. He further concluded that Ivanov's admission that "the skinheads wanted to close the [church's] drug rehabilitation center because it was having a negative effect on their drug trade" meant that "[t]he motivation of the skinheads was an intention to profit by criminal activity, rather than to punish [Iva-nov] *11and others for engaging in the Pentecostal faith." Finally, he found that Ivanov's fear of return to Russia was based on "the general lawlessness of the place," rather than abuse due to his religion.

As a result, the IJ found that Ivanov had not shown he experienced persecution "on account of' a protected ground, and thus he failed to qualify for asylum. Iva-nov therefore also fell short of the more stringent standard for withholding of removal. Finally, Ivanov's claim for CAT relief failed because there was no evidence that Ivanov had been or would be tortured at the hands of public officials or with the government's acquiescence if he returned to Russia. The IJ consequently denied Petitioners' applications but granted them voluntary departure.

Petitioners appealed. On review, the Board of Immigration Appeals (BIA) affirmed the IJ's decision without opinion. This appeal followed.

Standard of Review

Ordinarily, we review decisions of the BIA, not the IJ. Larios v. Holder, 608 F.3d 105, 107 (1st Cir.2010). However, where, as here, "the BIA summarily affirms the IJ's asylum determination, ... we review the IJ's decision as if it were the decision of the BIA." Id.

We review an IJ's findings of fact, including the determination of whether persecution occurred on account of a protected ground, under the familiar and deferential substantial evidence standard. Lopez de Hincapie v. Gonzales, 494 F.3d 213, 217 (1st Cir.2007). Under this rule, we respect the IJ's findings if "supported by reasonable, substantial, and probative evidence on the record considered as a whole." Larios, 608 F.3d at 107 (quoting Immigration & Naturalization Serv. v. Elias-Zacarias, 502 U.S. 478, 481, 112 S.Ct. 812, 117 L.Ed.2d 38 (1992)). However, "our deference is not unlimited," and "we may not affirm [the IJ's findings]" if "we cannot conscientiously find that the evidence supporting [them] is substantial, when viewed in the light that the record in its entirety furnishes, including the body of evidence opposed to the [IJ's] view." Kartasheva v. Holder, 582 F.3d 96, 105 (1st Cir.2009) (citations omitted) (internal quotation marks omitted). Indeed, we are obligated to reject the IJ's findings if a "reasonable adjudicator would be compelled to conclude to the contrary." Precetaj v. Holder, 649 F.3d 72, 75 (1st Cir.2011) (quoting 8 U.S.C. § 1252(b)(4)(b)).

Discussion

We begin with a brief overview of pertinent asylum law. To qualify for asylum, an alien must establish that he is a refugee. 8 U.S.C. § 1158(b)(1)(A). A refugee is a person who is -unable or unwilling to return to his homeland "because of persecution or a well-founded fear of persecution on account of race, religion, nationality, -membership in a particular social group, or political ■ opinion." 8 U.S.C. § 1101(a)(42). Proof of past persecution creates a presumption of a well-founded fear of future persecution that the government may rebut. Harutyunyan v. Gonzales, 421 F.3d 64, 67 (1st Cir.2005); see also 8 C.F.R. § 1208.13(b)(1).

Persecution is not defined by statute, but we know that it requires "more than ordinary harassment, mistreatment, or suffering." Lopez de Hincapie, 494 F.3d at 217. To constitute persecution, abuse "must have reached a fairly high threshold of seriousness, as well as some regularity and frequency." Rebenko v. Holder, 693 F.3d 87, 92 (1st Cir.2012) (quoting Alibeaj v. Gonzales, 469 F.3d 188, 191 (1st Cir.2006)) (internal quotation marks omitted).

*12Persecution also "always implies some connection to government action or inaction," whether in the form of direct government action, "government-supported action, or government's unwillingness or inability to control private conduct." Sok v. Mukasey, 526 F.3d 48, 54 (1st Cir.2008) (citations omitted) (internal quotation marks omitted); see also Burbiene v. Holder, 568 F.3d 251, 255 (1st Cir.2009). Local authorities' failure to respond to prior persecution may demonstrate a government's unwillingness or inability to control persecutors. Cf. Ortiz-Araniba v. Keisler, 505 F.3d 39, 42 (1st Cir.2007) (quoting Harutyunyan, 421 F.3d at 68) ("In determining whether a government is willing and able to control persecutors, ... a prompt response by local authorities to prior incidents is 'the most telling datum.' ").

For purposes of asylum, an alien must also demonstrate that the persecution he experienced occurred "on account of' a statutorily-protected ground. Lopez de Hincapie, 494 F.3d at 217. To meet this "nexus" requirement, an alien must provide sufficient evidence of an actual connection between the harm he suffered and his protected trait. Id. at 217-18. This does not require him "to identify [his] antagonists with absolute certainty," id. at 219, or "to show that the impermissible motivation was the sole motivation for the persecution," Sompotan v. Mukasey, 533 F.3d 63, 69 (1st Cir.2008) (citing In re S-P-, 21 I. & N. Dec. 486, 490 (BIA 1996)) (emphasis added). Rather, he must demonstrate only "that the persecution was based, 'at least in part,' on an impermissible motivation." Id. (quoting Sanchez Jimenez v. U.S. Att'y Gen., 492 F.3d 1223, 1232-33 (11th Cir.2007)).

In many asylum cases, the central issue is whether the applicant's story of past abuse is credible. Precetaj, 649 F.3d at 76. The IJ has "considerable latitude in evaluating credibility," and its assessment receives substantial weight. Id.

In this case, the IJ found that Iva-nov's testimony about the mistreatment he experienced was credible, generally internally consistent, and consistent with the record. Based on this testimony, the IJ observed it was "a close question" as to whether Ivanov established past persecution, but assumed for the purpose of discussion that he had done so. Relying on the IJ's credibility determination, we find that Ivanov met the past persecution threshold.

As outlined above, Ivanov testified about four specific occasions of mistreatment because of his Pentecostal faith within a four-year period: (1) when skinheads violently interrupted his baptism ceremony at a prayer house in November 1999; (2) when skinheads attacked him as he left the church-run drug rehabilitation center where he volunteered, beat him up, handcuffed and shocked him, and left him in a basement for three days without food and water in April 2002; (3) when skinheads attacked him in his apartment lobby a few days after he refused to comply with a federal security officer's forceful request that he testify against his pastor in March 2003; and (4) when unidentified assailants launched Molotov cocktails at his home in April 2003.

Ivanov also testified to a history of mistreatment of his congregation reaching back to his youth, including the repeated confiscation of religious literature, looting and burning of prayer houses, and violence against church members. Ivanov's testimony was consistent with U.S. State Department human rights reports describing the mistreatment of Pentecostals and persons of other minority religions in Russia, *13including incidents occurring on or around the anniversary of Hitler's birth.11

Considered together, these events suggest a pattern of escalating abuse directed at Ivanov beginning the day he was baptized and continuing until he left the country. The harm Ivanov suffered, particularly during his three-day detention in April 2002, rose above "ordinary harassment, mistreatment, or suffering." See Sok, 526 F.3d at 54 (six events occurring over the course of four years, considered together, suggested a pattern of abuse, where the most serious incident involved a three-day detention). Ivanov's mistreatment occurred regularly and with some frequency for four years. Viewed within the broader context of intolerance and abuse of Pentecostals in Russia as docu: mented in the U.S. .State Department human rights reports, these incidents reach the "fairly high threshold of seriousness" required of persecution. See Pulisir v. Mukasey, 524 F.3d 302, 308-09 (1st Cir.2008) ("Common sense suggests that larger social, cultural, and political forces can lend valuable context to particular incidents and, thus, can influence the weight that a factfinder may assign to those incidents.").

Seen in this context, these abuses also demonstrate the requisite nexus to government action or inaction. Here, Ivanov testified that his parents contacted the police when skinheads kidnapped him for three days in April 2002, but no follow-up action was taken. There is nothing in the record to suggest that Ivanov's abusers were ever apprehended, punished, or even looked for, in spite of having severely beaten and detained him for three days.12 This is consistent with reports that local authorities do not adequately respond to attacks against members of minority religious communities, including Pentecostals.13

Furthermore, skinheads attacked Ivanov in March 2003 only days after a federal security officer tried to intimidate him into testifying against his pastor. This fits with accounts that members of the federal security service "increasingly treat[] the leadership of some minority religious groups as security threats."14 It also aligns with religious leaders' apprehensions "that Russian government officials provide tacit or active support to a view held by many ethnic Russians that Orthodoxy is the country's so-called 'true reli*14gion.' "15 Moreover, it shows that local authorities have significant opportunities to restrict individuals' religious freedoms, leading to great variation between the laws on the books and national policies on the one hand, and the on-the-ground reality on the other.16

Ivanov contacted the police immediately after the March 2003 attack, but again no one came to his aid. As in April 2002, there is no evidence that the police made any efforts to apprehend or punish Iva-nov's attackers. It is no wonder Ivanov thought further attempts to elicit police assistance would be "futile."

Although the IJ did not credit Ivanov's assertion that skinheads were "used by the police as surrogates" or "aided and abetted by the authorities," Ivanov was not required to make such a showing to qualify for asylum. Ivanov had only to establish that the government was unable or unwilling to control the skinheads' actions, see Sok, 526 F.3d at 53, and it appears clear from the record that this is the case. Local authorities either failed to take action against, or perhaps even supported, Iva-nov's persecutors. Their failure to respond signals their unwillingness or inability to control Ivanov's persecutors.17 Cf. Ortiz-Araniba, 505 F.3d at 42. Accordingly, we make explicit what the IJ assumed and hold that Ivanov demonstrated past persecution linked to government action or inaction.

We next turn to the question of nexus to a protected ground. Although the IJ was willing to accept that Ivanov proved past persecution, he found that Ivanov did not establish a sufficient connection between the abuse he suffered and his religion. As set out above, the IJ provided two reasons for his finding: (1) he interpreted Ivanov's admission that skinheads opposed the drug rehabilitation center because of its negative impact on their drug trade as an indication that they were not punishing Ivanov for engaging in his Pentecostal faith; and (2) he concluded that Ivanov's fear of return to Russia was based on "the general lawlessness of the place, rather than mistreatment on account of' his religion. Considering the record as a whole, we are unable to find that either of these rationales or the IJ's ultimate determination was "supported by reasonable, substantial, and probative evidence." 18

First, the IJ's fixation on the skinheads' drug trade to the exclusion of any other motivation is misguided on principle and on fact. As a matter of principle, we do not require an alien to show that an impermissible motivation was the sole motivation for his persecution. Sompotan, 533 F.3d at 69. We have noted that aliens *15"seldom know the 'exact motivation[s]' of their persecutors and, of course, persecutors may often have more than one motivation." Id. (alteration in original) (quoting In re S-P-, 21 I. & N. Dec. at 490). Our sister circuits agree. See, e.g., Menghesha v. Gonzales, 450 F.3d 142, 148 (4th Cir.2006); Mohideen v. Gonzales, 416 F.3d 567, 570 (7th Cir.2005); Lukwago v. Ashcroft, 329 F.3d 157, 170 (3d Cir.2003); Girma v. Immigration & Naturalization Serv., 283 F.3d 664, 667 (5th Cir.2002); Borja v. Immigration & Naturalization Serv., 175 F.3d 732, 735-36 (9th Cir.1999) (en banc); Osorio v. Immigration & Naturalization Serv., 18 F.3d 1017, 1028 (2d Cir.1994).

The facts of this case illustrate the need for this principle. The IJ's determination that the skinheads were motivated only by their "intention to profit by criminal activity" ignores both the skinheads' overarching mission and the greater pattern of religiously-motivated abuse that Ivanov suffered. As Ivanov noted, the skinheads' raison d'etre is to "purify the Russian nation." They are notoriously xenophobic, racist, anti-Muslim, anti-Semitic, and, most relevantly here, intolerant of "adherents of 'foreign' religions."19 The skinheads who attacked Ivanov in April 2002 may indeed have had an economic interest in closing the church's drug rehabilitation center. But they also, at their core, undoubtedly opposed the center's religious mission and methods. The center's religious message was inseparable from the service it performed: church volunteers operated the center and rigorous bible study was integral to patients' treatment: Indeed, it appears that Ivanov's skinhead assailants recognized this and gave voice to their anti-religious motivation when they told Ivanov to find a way to close the "satanic" center. That those skinheads may have had an additional motive for attacking Iva-nov cannot reasonably be read to refute that they were also acting upon the central motive underlying their group identity.

This is especially true given the other abuse that Ivanov suffered. Remember, the April 2002 attack is only one of four events supporting Ivanov's asylum claim. In the other instances, Ivanov provided specific evidence of his attackers' anti-Pentecostal motivation. For example, in November 1999, skinheads attacked his baptism ceremony at a prayer house. In March 2003, skinheads attacked him a few days after he refused to testify against his pastor. In April 2003, unknown assailants threw Molotov cocktails at his house the same night that. someone attacked the church's drug rehabilitation center. Considered in view of the history of attacks against members of his church community and religious intolerance in Russia at-large, a reasonable adjudicator would be compelled to conclude that each of the attacks, including the attack in April 2002, was based, "at least in part," on the impermissible motivation of Ivanov's Pentecostal faith. See Sompotan, 533 F.3d at 69.

Second, the IJ's interpretation of Iva-nov's testimony that he feared "the same lawlessness" if he returned to Russia to mean that Ivanov feared "general lawlessness" in Russia runs counter to the record. The IJ appears to have construed Ivanov's statement out of context: Ivanov said he feared "the same lawlessness" immediately after he described the specific instances of abuse discussed above, but the IJ took him to mean he feared "lawlessness" in Russia generally. To the contrary, Ivanov consistently maintained in his application and testimony that he feared if he returned to Russia skinheads .or government authorities would harm him due to his religious *16beliefs.20 The IJ's monocular focus on Iva-nov's remark, to the exclusion of the balance of Ivanov's statements alleging specific fears of targeted persecution, is not supported by the record as a whole.

In sum, viewing the record in its entirety, including the evidence the IJ ignored or misconstrued, and relying on the IJ's own finding that Ivanov's testimony was generally credible, we cannot conscientiously find the IJ's determination that Ivanov did not establish the requisite nexus between the persecution he suffered and his Pentecostal faith is supported by substantial evidence. While we are mindful of the deferential nature of our standard of review, we are also cognizant of our obligation to reject the IJ's findings if, as here, a "reasonable adjudicator would be compelled to conclude to the contrary." See Precetaj, 649 F.3d at 75 (quoting 8 U.S.C. § 1252(b)(4)(b)). It is not the first time we have rejected an IJ's findings under this standard. See, e.g., id. at 76; Kartasheva, 582 F.3d at 105-06; Sok, 526 F.3d at 56, 58; Heng v. Gonzales, 493 F.3d 46, 49 (1st Cir.2007); Mukamusoni v. Ashcroft, 390 F.3d 110, 126 (1st Cir.2004). And so long as our review is not "a hollow exercise in rubber-stamping," we doubt it will be the last. See Cuko v. Mukasey, 522 F.3d 32, 41 (1st Cir.2008) (Cyr, J., dissenting).

We therefore find that Ivanov has established his eligibility for asylum. Accordingly, we have no need to proceed to Petitioners' requests for withholding of removal or relief under CAT, and we do not reach them here.

Conclusion

The order of the BIA affirming the IJ's decision is vacated and the matter is remanded for proceedings consistent with this decision.""")

# Case 14
add_case("""Amouri v. Holder
Court of Appeals for the First Circuit

Citations: 572 F.3d 29, 2009 WL 2020018
Docket Number: 19-1370
Panel: Michael Boudin, Kermit Victor Lipez, Bruce Marshall Selya
Judges: Boudin, Selya, Lipez
Other Dates: Submitted June 4, 2009.
Opinion
Authorities (30)
Cited By (47)
Summaries (11)
Similar Cases (44.1K)
PDF
Headmatter
Fatah AMOURI, Petitioner, v. Eric H. HOLDER, Jr., * Attorney General, Respondent.

No. 08-1993.

United States Court of Appeals, First Circuit.

Submitted June 4, 2009.
Decided July 14, 2009.

*31 Michael A. Paris and Cutler & Associates on brief for petitioner.

Michael F. Hertz, Assistant Attorney General, Civil Division, Hillel Smith and Anthony Wray Norwood, Trial Attorneys, Office of Immigration Litigation, on brief for respondent.

Before BOUDIN, SELYA and LIPEZ, Circuit Judges.
 * Pursuant to Fed. R.App. P. 43(c)(2), Attorney General Eric H. Holder, Jr. has been substituted for former Attorney General Michael B. Mukasey as the respondent. ↵
Combined Opinion by Selya
SELYA, Circuit Judge.
The petitioner, Fatah Amouri, is an Algerian national. He seeks judicial review of a decision of the Board of Immigration Appeals (BIA) ordering his removal and, in the process, denying his prayers for asylum, withholding of removal, and protection under the United Nations Convention Against Torture (CAT). As a part of his asseverational array, the petitioner advances a due process claim concerning the refusal of the immigration judge (IJ) to grant him a continuance. After careful consideration, we deny the petition.

I. BACKGROUND

We draw the facts from the IJ's supportable findings, augmented where necessary by excerpts from the overall record.

In March of 2001, the petitioner arrived in the United States without inspection. He remained here illegally. See 8 U.S.C. § 1182(a)(6)(A)(i). In 2005, he won a one-year visa in the Diversity Visa Lottery Program. See Carrillo-González v. INS, 353 F.3d 1077, 1078 n. 1 (9th Cir.2003) (explaining program). The petitioner's lottery win proved to be a Pyrrhic victory; he received the temporary one-year diversity visa but was deemed ineligible for immigrant status, see 8 U.S.C. § 1182(a)(6), and thus ineligible to receive anything more than the temporary visa.

To make matters worse, the lottery win apparently brought him to the attention of the authorities. On June 23, 2005, the government served him with a notice to appear in the immigration court.

The IJ granted a continuance at the petitioner's bequest so that he could explore the possibility of finding a way to take advantage of the lottery visa. Although the petitioner devised a scheme to gain eligibility for adjustment of status by *32 departing from the United States and reentering legally, he eventually abandoned that ploy. Instead, he applied for asylum, withholding of removal, and protection under the CAT.

The continuance that the IJ had granted served to adjourn the removal hearing to September 25, 2006. On that date the petitioner reported that he was unable to avail himself of the opportunity provided by his lottery win. Since the expiration of the one-year temporary visa was imminent, the IJ directed that the merits hearing commence forthwith.

The petitioner's counsel briefly protested that he had not expected to proceed to the merits then and there. The IJ explained why everyone should have anticipated precisely that eventuality. Counsel replied that it would be "okay" to begin immediately as long as he was given time to confer privately with his client. That request was honored. At no point did counsel assert that prejudice would result from going forward that day, nor did he suggest that delaying the trial would enhance the likely availability of additional documents or witnesses supporting the petitioner's averments.

The petitioner testified that he had suffered persecution in Algeria on account of his political opinion and that he feared future persecution should he be repatriated. Specifically, he related that he had managed a clothing and textiles shop owned by his father; that, in 2000, three or four armed men who identified themselves as "Muslim extremists" entered the store and demanded a large amount of money; and that he temporized by offering to pay the men at a future date. After the intruders left, he reported the incident to the police, who informed him that they would "work on it." They also advised him to take various precautions.

The petitioner decided to close the store and never made the demanded payment. The building was later torched, and the petitioner received a letter from the Islamic Army Group (IAG) charging that he had reneged on his religion and had been "sentenced ... to death." The police investigated the fire (although the petitioner kept the IAG letter to himself). The investigation proved fruitless.

In the meantime, the petitioner repaired to his grandmother's house in a different village some 800 kilometers away. He remained there for several months until learning that three or four armed men from the IAG had come looking for him. At that point, he fled to the United States.

Even though the one-year deadline for asylum petitions had expired long before the petitioner applied, the IJ allowed the asylum application to proceed based on a finding of extraordinary circumstances. See id. § 1158(a)(2); Chhay v. Mukasey, 540 F.3d 1, 5 (1st Cir.2008). The Attorney General does not challenge that determination, so we need not discuss the foundation on which it rests. Moreover, notwithstanding that the petitioner's testimony was inconsistent in certain particulars, the IJ deemed him generally credible.

Despite winning these battles, the petitioner lost the war. The IJ ruled that he had failed to demonstrate past persecution on account of a statutorily protected ground. In this regard, the IJ cited the petitioner's lack of any declared political affiliation and the absence of any indication that something other than unmitigated greed lay behind the attempted extortion and the subsequent threats.

The IJ rejected the application for withholding of removal on essentially the same basis. Furthermore, because there was no probative evidence that the Algerian government had either participated or ac *33 quiesced in the menacing conduct, the IJ dismissed the CAT claim.

The petitioner appealed to the BIA, without success. The BIA adopted the IJ's findings, reasoning, and conclusions, adding a few comments about the burden of proof. This timely petition for judicial review followed.

II. DISCUSSION

We begin our analysis with the asylum question. We move next to the petitioner's other claims for particularized forms of relief. Finally, we consider the alleged due process violation.

A. The Asylum, Claim.

To establish an entitlement to asylum, an alien must demonstrate that he is a refugee. 8 U.S.C. § 1158(b)(l)(B)(i); Lopez de Hincapié v. Gonzales, 494 F.3d 213, 217 (1st Cir.2007). To satisfy this requirement, the alien must show that he is unwilling or unable to return to his homeland for fear of "persecution on account of race, religion, nationality, membership in a particular social group, or political opinion." 8 U.S.C. § 1101(a)(42)(A); see, e.g., INS v. Cardoza-Fonseca, 480 U.S. 421, 428, 107 S.Ct. 1207, 94 L.Ed.2d 434 (1987); Makhoul v. Ashcroft, 387 F.3d 75, 79 (1st Cir. 2004). In turn, this entails a showing that the alien has a well-founded fear of future persecution based on one of the five statutorily enumerated grounds. Makhoul, 387 F.3d at 79. If the alien adduces probative evidence of past persecution on account of such a ground, that evidence creates a rebuttable presumption of a well-founded fear of future persecution. Id.

Persecution is a protean term, undefined by statute. To establish persecution, an alien must demonstrate that the harm (whether actual or feared) is more than the sum total of ordinary harassment or mistreatment. See Lopez de Hincapié, 494 F.3d at 217. We need not probe that point too deeply; this case involves claimed threats of murder — and threats of murder easily qualify as sufficiently severe harm. Id.

The "on account of' element comprises the linchpin between the harm and a statutorily protected ground. See Raza v. Gonzales, 484 F.3d 125, 128-29 (1st Cir.2007). To satisfy this nexus requirement, an alien must produce convincing evidence of a causal connection; that is, convincing evidence that the harm was premised on a statutorily protected ground. See Butt v. Keisler, 506 F.3d 86, 90 (1st Cir.2007); Lopez de Hincapié, 494 F.3d at 218.

Against this backdrop, we turn next to the applicable standard of review. Typically, this court reviews the BIA's decision. See Stroni v. Gonzales, 454 F.3d 82, 86 (1st Cir.2006). Here, however, the BIA adopted and summarily affirmed the IJ's findings and conclusions. Thus, we review the IJ's decision directly. See id. at 86-87. To the extent that the BIA has made additional comments, we review those comments as well. Id. at 87.

In conducting that review, the familiar substantial evidence rule applies. Under this rule, we accept the agency's factual findings as long as they are supported by substantial evidence in the record. See INS v. Elias-Zacarias, 502 U.S. 478, 481, 112 S.Ct. 812, 117 L.Ed.2d 38 (1992). This is a highly deferential standard; the agency's resolution of an issue of fact cannot be overturned unless the record compels a contrary conclusion. Id. at 481 n. 1. In other words, the record must point unerringly to the opposite conclusion. Laurent v. Ashcroft, 359 F.3d 59, 64 (1st Cir.2004); Aguilar-Solis v. INS, 168 F.3d 565, 569 (1st Cir.1999).

In this case, as in most cases, the determination as to whether the petitioner was *34 persecuted on account of a statutorily protected ground is a fact-sensitive determination. Thus, that determination engenders review under the substantial evidence rule. See Lopez de Hincapié, 494 F.3d at 218.

The petitioner argues that the IJ erred in this case because the attempted extortion and subsequent threats are compelling evidence that he was persecuted on account of his political opinion. We do not agree.

The IJ found that the most likely impetus for these acts was greed, not politics. The record contains no significantly probative evidence to the contrary. Accordingly, the petitioner has failed to forge the needed link between the harm and the statutorily protected ground.

The mere fact that the extortionists were associated with an extremist group does not compel a different conclusion. After all, fanaticism and a love of money are not mutually exclusive.

Here, moreover, the IJ supportably found no indication that the armed intruders wanted either to coerce the petitioner's adherence to their cause or to punish him for his beliefs. For aught that appears, the men wanted coin of the realm from Amouri, not political conformity.

Laboring to establish a nexus where none exists, the petitioner cites a case that (he says) stands for the proposition that extortion can be part and parcel of a systematic campaign of terror aimed at suppressing political opinion. See Joked v. INS, 356 F.3d 991, 998-99 (9th Cir.2004). That case, which involves a government agent's extortionate threat to reveal the petitioner's membership in an outlawed opposition party, is irrelevant here. As we have said, the record here reflects no meaningful ties between political affiliation and the demand for funds. 1

The petitioner argues that his refusal to honor the monetary demand was itself a manifestation of his political beliefs. This argument is made up out of whole cloth. There is not a shred of evidence in the record that even hints at, much less directly suggests, such an extraordinary leap of logic. The petitioner himself did not testify that this was in his mind, and the IJ surely was not compelled to pluck out of thin air a conclusion to that effect. See Chikkeur v. Mukasey, 514 F.3d 1381, 1383 (1st Cir.2008) (upholding a denial of asylum to alien who experienced extortion at the hands of a radical Islamist group and argued that his refusal to give them money was interpreted by them as an expression of political opinion); cf. Olympic Airways v. Husain, 540 U.S. 644, 653, 124 S.Ct. 1221, 157 L.Ed.2d 1146 (2006) (holding that an unsupported argument made in a brief was no more than a bald assertion that lacked probative value).

The petitioner's reliance on the death threat is equally misplaced. The petitioner points out that the threat referred to him as a "devil" and as one who had "renege[d]" on his religion. This phrasing, he says, evinces an association with political opinion. 2

This argument strains credulity. Although the threat used the quoted language, nothing in its context (or elsewhere in the record, for that matter) links that language to any particular political opinion. *35 Thus, we are not compelled to find that the threat was sparked by the petitioner's political viewpoint. See, e.g., Novoa-Umania v. INS, 896 F.2d 1, 5 (1st Cir.1990).

To say more about the asylum claim would be supererogatory. At best, the petitioner adduced evidence from which a sympathetic factfinder might perhaps have found in his favor. The law is settled, however, that when an IJ makes a choice between two plausible but conflicting inferences, his choice is necessarily supported by substantial evidence. See Lopez de Hincapié, 494 F.3d at 219; Aguilar-Solis, 168 F.3d at 571. Consequently, we uphold the denial of asylum.

B. Other Claims.

We give short shrift to the petitioner's remaining substantive claims. To petition successfully for withholding of removal, an alien must show that, if returned to his homeland, he would more likely than not be subjected to persecution on account of a statutorily protected ground. Pulisir v. Mukasey, 524 F.3d 302, 308 (1st Cir. 2008). The standard is one of clear probability. Cardoza-Fonseca, 480 U.S. at 430, 107 S.Ct. 1207; INS v. Stevic, 467 U.S. 407, 425, 430, 104 S.Ct. 2489, 81 L.Ed.2d 321 (1984). When an alien fails to establish a well-founded fear of persecution sufficient to ground an asylum claim, a counterpart claim for withholding of removal (that is, a claim premised on essentially the same facts) necessarily fails. See Lopez de Hincapié, 494 F.3d at 220; Makhoul, 387 F.3d at 82. So it is here.

This leaves the petitioner's CAT claim. To prevail on a CAT claim, an alien must prove that, if repatriated, he will more likely than not be subjected to torture with the consent or acquiescence of the government. See 8 C.F.R. §§ 1208.16(c), 1208.18(a)(1); see also Chhay, 540 F.3d at 7.

In support of his CAT claim, the petitioner relies on various State Department country conditions reports. Generally speaking, country conditions reports can be a valid source of evidence with respect to CAT claims. See, e.g., 8 C.F.R. § 1208.16(c)(3); Pulisir, 524 F.3d at 310. But even though country conditions reports are deemed generally authoritative in immigration proceedings, the contents of such reports do not necessarily override petitioner-specific facts — nor do they always supplant the need for particularized evidence in particular cases. See Zarouite v. Gonzales, 424 F.3d 60, 63-64 (1st Cir. 2005).

In this instance, the most that can be said is that, as the country conditions reports show, Algeria is a haven for terrorists and wracked by random violence. There is no evidence, however, that the government either participates or acquiesces in this violence.

The specific events at issue here indicate precisely the opposite. After the armed men visited the petitioner's shop, the police came to his aid. They agreed to investigate the matter and gave him safety tips. When, thereafter, his store burned down, the police again responded and carried out an investigation. On this record, there is no principled way that we can set aside the denial of the petitioner's CAT claim. See, e.g., Usman v. Holder, 566 F.3d 262, 268-69 (1st Cir.2009); De Oliveira v. Mukasey, 520 F.3d 78, 79 (1st Cir.2008).

C. The Due Process Claim.

This brings us to the petitioner's final assignment of error. That plaint arises out of the IJ's refusal to grant the petitioner a further continuance. It amounts to an allegation that the IJ committed a procedural due process violation and, as such, we review the BIA's sub

*36 silentio rejection of the claim de novo. 3 See Laurent, 359 F.3d at 62.

We pause to note that this claim may be waived. Although the petitioner's counsel originally objected to the order to go forward on September 25, he appears later to have withdrawn that objection by agreeing to proceed so long as he was given time to confer with his client. That request was granted.

We think that this series of events fairly can be construed as a withdrawal of the petitioner's earlier request for a further continuance. If so, the upshot would be a waiver of this assignment of error. See, e.g., United States v. Rodriguez, 311 F.3d 435, 437 (1st Cir.2002) (stating that a party who has withdrawn an objection has thereby waived the issue); Nimrod v. Sylvester, 369 F.2d 870, 872 (1st Cir.1966) (explaining that a party cannot advance on appeal an issue as to which he withdrew his objection).

In all events, we need not resolve the waiver question definitively. Because the claim of error is easily dispatched on other grounds, we take a more direct route.

Although an alien is not entitled to a letter-perfect removal hearing, his due process rights must be respected. See Pulisir, 524 F.3d at 311; Baires v. INS, 856 F.2d 89, 91 (9th Cir.1988). We see error here — but no prejudice and, thus, no affront to due process.

We need not tarry. The grant or denial of a continuance rests largely in the discretion of the trial judge. See, e.g., United States v. Flecha-Maldonado, 373 F.3d 170, 175 (1st Cir.2004); Macaulay v. Anas, 321 F.3d 45, 49 (1st Cir.2003). While that authority must be exercised judiciously and with an eye toward fundamental fairness, even the arbitrary denial of a continuance cannot sink to the level of a due process violation unless it results in actual prejudice. See Pulisir, 524 F.3d at 311; United States v. Saccoccia, 58 F.3d 754, 770-71 (1st Cir.1995); United States v. Lussier, 929 F.2d 25, 28-29 (1st Cir. 1991).

"A court will find such prejudice only when it is shown that an abridgement of due process is likely to have affected the outcome of the proceedings." Pulisir, 524 F.3d at 311. It is not enough for a party to claim conclusorily that, had he been granted a continuance, he could have presented additional evidence; rather, he must give a reviewing court some indication of what that evidence would have comprised and how additional time would have allowed him to gather it. See United States v. Rodriguez-Duran, 507 F.3d 749, 765 (1st Cir.2007). He also must show that the new evidence would likely have altered the outcome of the proceeding. See Shmykelskyy v. Gonzales, 477 F.3d 474, 482 (7th Cir.2007).

Here, the petitioner was the lone witness in his own behalf. He offered some documentary evidence. But he made no effort either to call any other witnesses or to offer any other documentary evidence. More importantly, he did not identify below and has not identified here any such witnesses or documents. Instead, he relies exclusively on vague assertions about additional (unnamed) witnesses and additional (unspecified) documents that might have bolstered his testimony. Without some more concrete demonstration that *37 such witnesses and documents existed, were not available at the hearing, and would have supported his story, we can make no finding of prejudice. Consequently, the petitioner's due process claim founders.

III. CONCLUSION

We need go no further. For the reasons elucidated above, we deny the petition for judicial review.

So Ordered.""")

# Case 15
add_case("""Sunoto v. Gonzales
Court of Appeals for the First Circuit

Citations: 504 F.3d 56, 2007 WL 2792894, 2007 U.S. App. LEXIS 22822
Docket Number: 06-1366
Judges: Lipez, Gibson, Stahl
Other Dates: Submitted Feb. 5, 2007.
Opinion
Authorities (7)
Cited By (29)
Summaries (4)
Similar Cases (9.2K)
PDF
Headmatter
Sunoto SUNOTO, Petitioner, v. Alberto GONZALES, Attorney General of the United States, Respondent.

No. 06-1366.

United States Court of Appeals, First Circuit.

Submitted Feb. 5, 2007.
Decided Sept. 27, 2007.

*57 William A. Hahn and Hahn & Matkov on brief for petitioner.

Hillel R. Smith, Trial Attorney, Office of Immigration Litigation, Civil Division, United States Department of Justice, Peter D. Keisler, Assistant Attorney General, Greg D. Mack, Senior Litigation Counsel, on brief for respondent.

Before LIPEZ, Circuit Judge, GIBSON * and STAHL, Senior Circuit Judges.
 * Of the United States Court of Appeals for the Eighth Circuit, sitting by designation. ↵
Combined Opinion by Kermit Victor Lipez
LIPEZ, Circuit Judge.
Sunoto, a native and citizen of Indonesia, petitions for review of a decision of the Board of Immigration Appeals ("BIA") affirming the denial of his application for asylum, withholding of removal and voluntary departure. An Immigration Judge ("IJ") found that Sunoto was not eligible for relief because, inter alia, he originally submitted a fraudulent application and failed to present credible testimony in support of his amended application. The BIA adopted and affirmed the IJ's decision. Sunoto challenges the IJ's decision on a host of grounds, most of which were not raised in his appeal to the BIA. On those omitted issues, he unquestionably failed to exhaust his administrative remedies, see 8 U.S.C. § 1252(d)(1), leaving us without jurisdiction to review the agency's decision on those issues. Berrio-Barrera v. Gonzales, 460 F.3d 163, 167 (1st Cir.2006). Two issues may be deemed preserved only if his BIA submissions are viewed generously. Those issues are, in any event, unavailing, and we therefore deny the petition for review.

I.

Sunoto 1 lawfully entered the United States in July 1991 as a non-immigrant alien in transit and was authorized to remain in the country until the end of August that same year. On June 3, 2002, he filed an asylum application with the former Immigration and Naturalization Service claiming that he was a Christian who feared Muslim extremists in his native Indonesia. Among other past episodes described in the application, he claimed that his father, a church deacon, had been shot and killed by the extremists. He reiterated this background in an interview with an asylum officer.

More than two years later, while removal proceedings were pending against him, *58 Sunoto filed a new asylum application and admitted that his earlier application was almost entirely false. He explained at a hearing before an IJ that he had allowed an individual with whom he lived to fabricate the facts in the first application because Sunoto was newly arrived in the United States, he "did not know anything," and he "did not want to argue because [he] did not want to make that person angry." Sunoto admitted that, in fact, he had become a Christian only after arriving in the United States, and neither he nor any family members had experienced mistreatment in Indonesia. However, he repeated his fear of future persecution based on his newly adopted Christian beliefs.

In an oral ruling, the IJ denied Sunoto's application for asylum and withholding of removal, and also found that he was not entitled to protection under the Convention Against Torture. 2 The IJ found Suno-to statutorily ineligible for asylum on two grounds: (1) his revised application was untimely because it was not filed within one year of his arrival in the United States, see 8 U.S.C. § 1158(a)(2)(B), and (2) Sunoto knowingly filed a frivolous application for asylum, and gave fraudulent and fabricated testimony before an asylum officer, disqualifying him from obtaining benefits under the Immigration and Naturalization Act, see 8 U.S.C. § 1158(d)(6). The IJ alternatively concluded that Sunoto had failed to present credible testimony in support of his application, finding Sunoto to be "evasive, nonresponsive, furtive, and a wholly incredible witness." In making the credibility finding, the IJ pointed to inconsistencies in Sunoto's testimony at the hearing, his admittedly fraudulent first application, the subsequent false testimony he gave to the asylum officer, and his explanation for his earlier conduct — which the IJ termed "disingenuous at best." The negative credibility finding also doomed Sunoto's request for withholding of removal. See Abdullah v. Gonzales, 461 F.3d 92, 97 (1st Cir.2006) ("An alien who fails to satisfy the standard for asylum automatically fails to satisfy the more stringent standard for withholding of removal.").

In his notice of appeal to the BIA, which apparently was filed without the assistance of counsel, Sunoto complained that "[t]he judge was not fair enough to listen to my testimony" and asserted that "I told everything the truth, but the judge said I was lie." A subsequently filed "brief' consisted of a three-page statement describing his conversion to Christianity, the absence of religious freedom in Indonesia, and his fear that he would be a target of persecution if he returned there. In reference to his first application, he explained: "I realized that my application for asylum was fraud. The reason I changed my affidavit on the hearing last year just because I couldn't lie to myself anymore. I already received the truth from God. I convinced myself always to tell the truth to everyone." Attached to his statement were copies of news reports about religious violence in Indonesia.

The BIA adopted and affirmed the IJ's decision in February 2006. It declined to decide whether Sunoto's second application was timely filed, but agreed with the IJ that he was in any event ineligible for asylum because he had filed a frivolous application. Although the Board disagreed with the IJ's finding of inconsistencies in Sunoto's testimony, 3 it agreed that *59 he was not a credible witness based on the other reasons cited by the IJ and that he therefore failed to prove his claim for withholding of removal. The BIA also endorsed the IJ's rejection of voluntary departure. It treated Sunoto's submission of new documents as a motion to remand, but concluded that, given the adverse credibility finding, he could not meet his "heavy burden" to prove a likely change in result if the proceedings were reopened. See Abdullah, 461 F.3d at 100 (referring to the "heavy burden" faced by an alien seeking to reopen immigration proceedings).

In his petition for review to this court, Sunoto presents six issues: (1) the IJ erred as a matter of law in ruling that his fraudulent application permanently barred him from receiving any immigration benefits; (2) the IJ erroneously ruled that his amended asylum application was untimely; (3) the BIA erroneously failed to give full effect to its finding that the IJ improperly identified inconsistencies in his hearing testimony; (4) the IJ improperly used an irrebuttable presumption that he was incapable of telling the truth; (5) the IJ's "clear predisposition" to find that he was incapable of telling the truth denied him due process of law; and (6) the case must be remanded because the IJ did not rule on his amended application.

As revealed by our description of Sunoto's notice of appeal and supporting materials, none of these claims was explicitly presented to the BIA. A petitioner who fails to present a claim to the BIA has failed to exhaust his administrative remedies on that issue, and we consequently lack jurisdiction to review the claim. Berrio-Barrera, 460 F.3d at 167; see also Olujoke v. Gonzales, 411 F.3d 16, 23 (1st Cir.2005).

However, among the six asserted challenges in Sunoto's brief are two focusing on the IJ's credibility finding — the ir-rebuttable presumption and due process claims — that resemble his contentions to the BIA that the IJ was unfair in not listening to his testimony and called him "a lie." Whether the similarity is enough to warrant our review is doubtful. The exhaustion of remedies doctrine extends not only to claims omitted from an appeal to the BIA but also to claims that were "insufficiently developed before the BIA." Silva v. Gonzales, 463 F.3d 68, 72 (1st Cir. 2006); Olujoke, 411 F.3d at 22-23. 4 Nonetheless, preferring to apply this standard generously, we briefly consider his objections concerning the IJ's approach toward his truthfulness.

II.

When the BIA adopts and affirms an IJ's decision, we review the IJ's *60 decision "to the extent of the adoption, and the BIA's decision as to [any] additional ground." Berrio-Barrera, 460 F.3d at 167; see also Chen v. Ashcroft, 376 F.3d 215, 222 (3d Cir.2004) ("[W]hen the BIA both adopts the findings of the IJ and discusses some of the bases for the IJ's decision, we have authority to review the decisions of both the IJ and the BIA."). In conducting our review, we use the deferential substantial evidence standard for factual findings and credibility determinations. Silva, 463 F.3d at 72. That approach requires us to "uphold the BIA's decision 'unless any reasonable adjudicator would be compelled to conclude to the contrary.' " Id. (quoting 8 U.S.C. § 1252(b)(4)(B)).

At bottom, Sunoto's due process and irrebuttable presumption claims are both assertions that the IJ unfairly relied on the fraudulent application in making the adverse credibility finding, and lacked a sufficient basis in the record for that finding. The BIA determined that the IJ erred with respect to one rationale — that Sunoto had testified inconsistently about his knowledge of the contents of his fraudulent application — but held that the finding was sufficiently supported by other factors: "the respondent's fraudulent filing and testimony before the asylum office, his demeanor, [and] his implausible explanation for why he pursued a fraudulent claim...."

Sunoto does not challenge the relevance and validity of these other reasons; indeed, it cannot be debated that his earlier fabrications carry some weight. However, he claims that the IJ began the credibility assessment with an unfair emphasis on his past conduct and then unfairly bolstered the inference of untruthfulness by relying heavily on the inconsistency that the BIA rejected. Sunoto cites several comments made by the IJ, including that "[t]his respondent is incapable of telling the truth," and that "this Court cannot find anything that comes out of the respondent's mouth or anything that he submits to this Court in writing to be credible." Sunoto argues that the predisposition reflected in this "strong language" is "particularly objectionable because it is based on a view of Sunoto's testimony that the BIA has found unwarranted." He further asserts that these statements suggest a predisposition that diminishes the force of the other factors cited by the IJ and prevented him from having a fair hearing. 5

While the IJ's credibility determination undoubtedly was influenced to some extent by his erroneous finding of an inconsistency, he cited — as noted above — multiple other reasons for his conclusion and observed that "[a]ll of these actions go to the heart of the matter before this Court today, that is, is the respondent a credible witness." For example, in rejecting Suno-to's explanation that he filed the fraudulent application because he feared confronting his friend, the IJ observed that if he were "afraid to contradict his roommate and change his asylum application because he thought he would be kicked out of his house, [he] certainly would have refused to *61 go under oath and perjure himself in such grave and great detail before the United States asylum officer." The IJ thus found that Sunoto was "a full, willing participant in this fraud on the United States."

We therefore are persuaded that the IJ did not, as Sunoto suggests, prejudge his credibility. Rather, the judge deemed his new story unbelievable and, among other reasons, factored in his assessment of demeanor. Moreover, the BIA reviewed the record with care, discounting the IJ's subsidiary finding of inconsistency. 6 On this record, we cannot say that the IJ's credibility finding was unfairly derived or that the nature of the proceedings compelled the BIA to reject the IJ's credibility determination.

The petition for review is denied.""")

# Case 16
add_case("""Arevalo-Giron v. Holder, Jr.
Court of Appeals for the First Circuit

Citations: 667 F.3d 79, 2012 WL 266024
Docket Number: 10-2357
Judges: Lynch, Torruella, Selya
Other Dates: Submitted Dec. 6, 2011.
Opinion
Authorities (13)
Cited By (21)
Summaries (5)
Similar Cases (21.9K)
PDF
Headmatter
Marlene Lisbeth ARÉVALO-GIRÓN, Petitioner, v. Eric H. HOLDER, Jr., Attorney General, Respondent.

No. 10-2357.

United States Court of Appeals, First Circuit.

Submitted Dec. 6, 2011.
Decided Jan. 31, 2012.

*81 Stephen M. Born and Mills & Born on brief for petitioner.

Tony West, Assistant Attorney General, Civil Division, United States Department of Justice, William C. Peachey, Assistant Director, Office of Immigration Litigation, and Ada E. Bosque, Senior Litigation Counsel, Office of Immigration Litigation, on brief for respondent.

Before LYNCH, Chief Judge, TORRUELLA and SELYA, Circuit Judges.
Combined Opinion by Selya
SELYA, Circuit Judge.
The petitioner, Marlene Lisbeth Arévalo-Girón, is a Guatemalan national. She seeks judicial review of a final order of the Board of Immigration Appeals (BIA) denying her application for withholding of removal. After careful consideration, we deny the petition.

The petitioner entered the United States on November 1, 1997, without inspection. Some ten years later, the Department of Homeland Security discovered her presence and initiated removal proceedings against her. See 8 U.S.C. § 1182(a)(6)(A)®; id. § 1229a(a)(2).

Before the immigration judge (IJ), the petitioner conceded removability but cross-applied for asylum, withholding of removal, and protection under the United States Convention Against Torture (CAT). In support, she asserted that if returned to Guatemala, she would face persecution on account of her status as either a single woman with perceived wealth or a former "child of war." The IJ determined that her claim for asylum was time-barred; denied withholding of removal on the ground that she had failed to demonstrate a likelihood of persecution in Guatemala on account of a statutorily protected status; and dismissed her entreaty for CAT relief because she had not shown any governmental involvement in the feared harm.

The BIA affirmed the IJ's decision. This timely petition for judicial review followed. In it, the petitioner challenges only the denial of withholding of removal. 1

Because the BIA added its own gloss to the IJ's reasoning, we review the two decisions as a unit. See Lopez Perez v. Holder, 587 F.3d 456, 460 (1st Cir.2009). In conducting that review, we test the agency's factual findings, including credibility determinations, under the familiar substantial evidence rule. Morgan v. Holder, 634 F.3d 53, 56-57 (1st Cir.2011). This rule requires us to accept all factual findings that are "supported by reasonable, substantial, and probative evidence on the record considered as a whole." Nikijuluw v. Gonzales, 427 F.3d 115, 120 (1st Cir.2005) (quoting INS v. Elias-Zacarias, 502 U.S. 478, 481, 112 S.Ct. 812, 117 L.Ed.2d 38 (1992)) (internal quotation *82 marks omitted). In other words, we must uphold such a finding unless the record compels a contrary conclusion. See 8 U.S.C. § 1252(b)(4)(B); Sompotan v. Mukasey, 533 F.3d 63, 68 (1st Cir.2008). By contrast, we review legal conclusions de novo, ceding some deference, however, to the agency's interpretation of statutes and regulations that fall within its purview. See Mendez-Barrera v. Holder, 602 F.3d 21, 24 (1st Cir.2010).

To prove an entitlement to withholding of removal, an alien bears the burden of demonstrating a clear probability that her life or freedom would be threatened in her homeland on account of her race, religion, nationality, membership in a particular social group, or political opinion. See 8 U.S.C. § 1231(b)(3)(A); 8 C.F.R. § 208.16(b); see also Morgan, 634 F.3d at 60. This burden can be carried in two ways: the alien can show either that she has suffered past persecution (giving rise to a rebuttable presumption of future persecution) or that, upon repatriation, a likelihood of future persecution independently exists. See López-Castro v. Holder, 577 F.3d 49, 52 (1st Cir.2009); 8 C.F.R. § 208.16(b)(l)-(2). Regardless of which path the alien travels, she must establish a connection between the feared harm and one of the five statutorily protected grounds. See Lopez Perez, 587 F.3d at 462; López-Castro, 577 F.3d at 54.

In the case at hand, the petitioner claims that if she returns to Guatemala, she will be persecuted due to her membership in either of two social groups: single women perceived to have substantial economic resources 2 or former children of war. We doubt whether either group is legally cognizable. See Mendez-Barrera, 602 F.3d at 25 (limning requirements for cognizable social group); see also Scatambuli v. Holder, 558 F.3d 53, 59 (1st Cir. 2009) (suggesting that "affluent Guatemalans" do not compose a cognizable group). But we need not make so broad a holding to resolve the petitioner's claim. Rather, we uphold the agency's finding that any potential hardship faced by the petitioner in Guatemala would be unrelated to her membership in either of these purported social groups.

Refined to bare essence, the petitioner makes two arguments. First, she attempts to create a presumption of future persecution by describing incidents and facts that she characterizes as past persecution: the murder of her father by an unknown assailant; the drafting of her brothers into the civil patrol; and her lack of education. The agency determined that these hardships were the result of Guatemala's horrific civil war, not the petitioner's membership in the putative social group comprising former children of the war. This determination is supported by substantial evidence or, more precisely, by the absence of anything in the record linking the described incidents and facts to any particular status. For aught that appears, the petitioner was simply in the wrong place at the wrong time.

We note, moreover, that the petitioner herself testified that her father was not a member of either the army, the guerillas, or the civil patrol. This testimony supports the agency's determination that he was a random casualty of the civil war. By the same token, the petitioner's lack of education and her brothers' compelled participation in the civil patrol — to the extent that these facts might conceivably consti *83 tute persecution at all, cf. Aguilar-Solis v. INS, 168 F.3d 565, 572 (1st Cir.1999) ("Danger resulting from participation in general civil strife, without more, does not constitute persecution.") — were never tied to the petitioner's purported status as a former "child of war." These deficits are fatal to her claim of past persecution. See Lopez Perez, 587 F.3d at 462-63 (rejecting claim for withholding of removal where record lacked evidence that past persecution resulted from protected status).

The petitioner's remaining claim is no more robust. She asserts that, if removed, she will be targeted by violent gangs in Guatemala because she is a single woman perceived to have substantial economic resources. To bolster this claim, she testified that her family members were the victims of gang-related robberies, and she provided documentation regarding the prevalence of violence against women in Guatemala. The agency concluded, however, that the violence in Guatemala is indiscriminate and that the gangs do not target any particular social group. This conclusion is fully supported by the record.

We need not tarry. There is no evidence in the record that the gangs specifically target women. The petitioner herself never testified to that effect; to the contrary, she stated that the gangs were only interested in increasing their wealth.

Nor does the State Department country conditions report cited by the petitioner materially alter the decisional calculus. This report describes how violence against women is, regrettably, an ongoing problem in Guatemala. Nevertheless, the report does not focus on economic considerations but, rather, suggests that the violence in Guatemala, though widespread, is not aimed at any particular segment of society. See Palma-Mazariegos v. Gonzales, 428 F.3d 30, 37 (1st Cir.2005) (rejecting withholding of removal claim where State Department report "attests that the threat of violence afflicts all Guatemalans to a roughly equal extent, regardless of their membership in a particular group or class"). At any rate, the situation described in the report is not so pervasive as to compel the conclusion that the petitioner is likely to suffer harm upon her return to her homeland.

Let us be perfectly clear. There is simply no evidence that women with substantial economic resources, whether single or married, are more attractive targets for Guatemalan gangs than men with fat wallets. Fairly viewed, greed — not social group membership — is the apparent trigger for the gangs' interest, see Lopez de Hincapié v. Gonzales, 494 F.3d 213, 219 (1st Cir.2007) (rejecting claim for withholding of removal where evidence suggested that petitioner was targeted "because of greed, not because of her political opinion or membership in a particular social group"), and mere vulnerability to criminal predations cannot define a cognizable social group, see, e.g., Sicajur-Diaz v. Holder, 663 F.3d 1, 4 (1st Cir.2011).

To cinch matters, persecution requires some nexus to the government. See López-Castro, 577 F.3d at 55 (rejecting claim for withholding of removal where petitioner failed to link feared gang violence with Guatemalan government). Here, however, the petitioner has not shown any connection between the violence that she fears and the government of Guatemala.

We need go no further. For the reasons elucidated above, we deny the petition for judicial review.

So Ordered.""")

# Case 17
add_case("""Cabrera v. Lynch
Court of Appeals for the First Circuit

Citations: 805 F.3d 391, 2015 WL 6859309
Docket Number: 14-1690P
Judges: Howard, Selya, Thompson
Opinion
Authorities (17)
Cited By (11)
Summaries (0)
Similar Cases (7.4K)
PDF
Headmatter
Julia Mercedes CABRERA, Petitioner, v. Loretta E. LYNCH, * Attorney General, Respondent.

No. 14-1690.

United States Court of Appeals, First Circuit.

Nov. 9, 2015.

*392 Livia Lungulescu and Romanovsky Law Offices on brief for petitioner.

Benjamin C. Mizer, Acting Assistant Attorney General, Civil Division, United States Department of Justice, Ernesto H. Molina, Jr., Assistant Director, Office of Immigration Litigation, and Joanna L. Watson, Trial Attorney, Office of Immigration Litigation, on brief for respondent.

Before HOWARD, Chief Judge, SELYA and THOMPSON, Circuit Judges.
 * Pursuant to Fed. R.App. P. 43(c)(2), Attorney General Loretta E. Lynch has been substituted for former Attorney General Eric H. Holder, Jr. as the respondent. ↵
Combined Opinion by Selya
SELYA, Circuit Judge.
The petitioner, Julia Mercedes Cabrera, is a native and citizen of the Dominican Republic. She seeks judicial review of a final order of the Board of Immigration Appeals (BIA) upholding a decision of an immigration judge (IJ), which denied her both an 1-751 waiver and cancellation of removal. After careful consideration, we deny her petition.

I. BACKGROUND

We briefly rehearse the facts and travel of the case. The petitioner entered the United States in January of 1991 and married a U.S. citizen later that same year. Through that marriage, she was able to acquire status as a conditional lawful permanent resident on June 25, 1993. See 8 U.S.C. § 1186a(a)(1), (h)(1). The petitioner and her spouse subsequently filed an 1751 joint petition (the joint petition) seeking to remove the conditional nature of the petitioner's residency status. See id. § 1186a(c)(l).

Following an interview in early 1996, the Immigration and Naturalization Service notified the petitioner of its intent to deny the joint petition based on a finding of marriage fraud. The joint petition was formally denied on August 8, 1997, resulting in the termination of the petitioner's status as a conditional lawful permanent resident. The petitioner never sought review of this adverse determination. Shortly thereafter, the petitioner and her spouse became embroiled in divorce proceedings and a final divorce decree was entered on June 18,1999.

In October of 2000, federal authorities placed the petitioner in removal proceedings. The next year (while still in removal proceedings), the petitioner filed another 1-751 petition. This petition (the waiver petition) sought a waiver of the joint petition requirements, maintaining that the petitioner had entered into her marriage in good faith. See id. § 1186a(e)(4).

The waiver petition proved unavailing: United States Citizenship and Immigration Services (USCIS) denied it on October 5, 2006. In doing so, USCIS did not consider the merits of the waiver petition but, rather, relied on the previous finding of marriage fraud. USCIS explained that the marriage fraud finding rendered the petitioner ineligible to seek a waiver of the joint filing requirement.

The removal proceedings were resumed and, in April of 2012, the petitioner appeared for a merits hearing. The IJ asked the petitioner whether she was seeking review of the denial of her joint petition or the denial of her waiver petition. The petitioner confirmed that she was seeking review only of the denial of the waiver petition.

At the end of the hearing, the IJ upheld the denial of the waiver petition. She found that the petitioner had not carried her burden of proving that she had entered into her marriage in good faith. Re-latedly, the IJ found that the petitioner was ineligible for cancellation of removal under 8 U.S.C. § 1229b(a) and, thus, pre-termitted her application.

*393 The petitioner timely appealed to the BIA, which affirmed the IJ's decision and dismissed the appeal. This timely petition for judicial review followed.

II. ANALYSIS

Our analysis necessarily begins with the standard of review. In immigration cases, judicial oversight ordinarily focuses on the final order of the BIA. See Moreno v. Holder, 749 F.3d 40, 43 (1st Cir.2014). "But where, as here, the BIA accepts the IJ's findings and reasoning yet adds its own gloss, we review the two decisions as a unit." Id. (quoting Xian Tong Dong v. Holder, 696 F.3d 121, 123 (1st Cir.2012)). Claims of legal error engender de novo review, with some deference to the agency's expertise in interpreting both the statutes that govern its operations and its own implementing regulations. See Jianli Chen v. Holder, 703 F.3d 17, 21 (1st Cir.2012); see also Chevron, U.S.A., Inc. v. Nat. Res. Def. Council, Inc., 467 U.S. 837, 843-44, 104 S.Ct. 2778, 81 L.Ed.2d 694 (1984).

We turn next to the relevant legal framework under the Immigration and Nationality Act (the Act). Under the Act, an alien married to a U.S. citizen for. less than 2 years may seek status as a conditional lawful permanent resident. See 8 U.S.C. § 1186a(a)(1), (h)(1). If conditional residency status is granted, the alien must apply for removal of her conditional status within the 90-day window preceding the second anniversary of the date on which that status was acquired. See id. § 1186a(c)(1l), (d)(2)(A); see also Reynoso v. Holder, 711 F.3d 199, 202 n. 4 (1st Cir.2013).

The application process for the removal of conditional status entails two steps: first, the alien and the citizen spouse must jointly submit a Form 1-751 petition attesting to the validity and bona fides of the marriage; second, both spouses must appear for an interview conducted by a Department of Homeland Security (DHS) representative. See 8 U.S.C. § 1186a(c)(1), (d)(3). If the joint petition is unsuccessful, then the alien's status as a conditional lawful permanent resident terminates, and DHS will proceed to initiate removal proceedings. See 8 U.S.C. § 1186a(c)(3)(C); 8 C.F.R. § 216.4(d)(2); see also Reynoso, 711 F.3d at 202 n. 4.

An alien whose joint petition is denied may seek review of the adverse determination in her subsequent removal proceedings. See 8 C.F.R. § 216.4(d)(2). In that event, the government has the burden of proving by a preponderance of the evidence that the material facts alleged in the joint petition are false. See id.

There is another path that may be open to an alien who cannot satisfy the requirements for the granting of an 1-751 joint petition. Such an alien may file a petition for a waiver of the joint filing requirements. See 8 U.S.C. § 1186a(c)(4); 8 C.F.R. § 1216.5(a)(1). The alien may qualify for this sort of discretionary waiver by demonstrating, among other things, that she entered into the qualifying marriage "in good faith"; that "the qualifying marriage has been terminated (other than through the death of the spouse)"; and that she "was not at fault in failing to meet the requirements [for a joint petition]." 8 U.S.C. § 1186a(e)(4)(B). Under this framework, the burden of proof rests with the alien to show that she entered into the qualifying marriage in good faith. See id. § 1186a(c)(4); McKenzie-Francisco v. Holder, 662 F.3d 584, 586-87 (1st Cir.2011). An alien whose waiver petition is denied may seek review of that decision in her removal proceedings. See 8 C.F.R. § 1216.5(f).

Against this backdrop, we examine the petitioner's twin claims of error. First, *394 she asserts that the IJ erroneously reviewed the waiver petition instead of the joint petition, leading to an improper shift in the burden of proof. Second, she asserts that the BIA blundered in determining that she was statutorily ineligible for cancellation of removal. We address these claims of error sequentially.

A. •

■ The petitioner's first contention need, not detain us. At the removal hearing, the IJ made a specific point of clarifying which petition was at issue. ' The petitioner, through her attorney, assured the IJ in no uncertain terms that she was seeking review only of the waiver petition, not of the joint petition.

That ends this aspect of the matter. It is axiomatic that a litigant is bound by her strategic choices during the course of a legal proceeding. See Genereux v. Raytheon Co., 754 F.3d 51, 59 (1st Cir.2014). If a particular strategy later proves unavailing, the litigant cannot forsake her earlier tactical decision at will and "attempt to change horses midstream in hopes of finding a swifter steed." Id. This construct has particular force where, as here, a litigant or her attorney makes an express representation to both the trial judge and the opposing party. See id. at 58-59.

This case aptly illustrates the point. Through her counsel, the petitioner explicitly and emphatically informed the IJ of her decision to seek review only of the waiver petition. Both judges and opposing parties must be able to rely on such representations, and nothing in this record suggests any valid reason why the petitioner should not be firmly bound by her own strategic choice. 1

B.

This brings us to the petitioner's contention that the BIA erred in determining that she was ineligible to apply for cancellation of removal under section 1229b(a). With respect to this contention, the petitioner urges us to review the decision of the IJ directly because the BIA failed to offer any independent reasoning for its views on this point.

This exhortation lacks force. We treat the conclusions of an IJ as those of the BIA only when the BIA affirms the IJ without opinion. See, e.g., Keo v. Ashcroft, 341 F.3d 57, 59-60 (1st Cir.2003); Herbert v. Ashcroft, 325 F.3d 68, 70-71 (1st Cir.2003). This is not such a case: here, the BIA added its own gloss to the IJ's findings and reasoning. Thus, we train the lens of our inquiry on the combination of the BIA's decision and the IJ's decision. See Moreno, 749 F.3d at 43; Xian Tong Dong, 696 F.3d at 123.

An alien who holds lawful permanent resident status may obtain cancellation of removal only if she: (i) "has been ... lawfully admitted for permanent residence" for at least five years; (ii) "has resided in the United States continuously for seven years" after her admission in any status; and (iii) "has not been convicted of any aggravated felony." 8 U.S.C. § 1229b(a)(1)-(3). Even if an alien satisfies these three prerequisites, the Attorney General's decision to grant such relief is discretionary and "amounts to 'an act of grace.' " Sad v. INS, 246 F.3d 811, 819 (6th Cir.2001) (quoting INS v. Yueh-Shaio Yang, 519 U.S. 26, 30, 117 S.Ct. 350, 136 L.Ed.2d 288 (1996)).

*395 In the ease at hand, the petitioner falls well short of the required showing. She was, at most, a conditional lawful permanent resident from June 1993 through August 1997 — a period of less than five years. This failure to satisfy the five-year prerequisite is, in itself, enough to find her ineligible for cancellation of removal under section 1229b(a).

In all events, the petitioner lost even this conditional status when USCIS formally denied the joint petition. See 8 U.S.C. § 1186a(c)(3)(C); 8 C.F.R. § 216.4(d)(2). Nor did the filing of the waiver petition serve to restore her residency status. See Severino v. Mukasey, 549 F.3d 79, 83 (2d Cir.2008). Because the petitioner had no status as a permanent resident, conditional or otherwise, when she filed the waiver petition, the BIA correctly determined that she was categorically ineligible to apply for cancellation of removal under 8 U.S.C. § 1229b(a). See id. at 8283 (affirming alien's ineligibility for cancellation of removal under 8 U.S.C. § 1229b(a) because his conditional lawful permanent residency status had been terminated); see also Padilla-Romero v. Holder, 611 F.3d 1011, 1013 (9th Cir.2010) ("[T]he text requires that an alien applying for cancellation of removal under § 1229b(a) have current [lawful permanent residence] status.").

In an effort to undermine this reasoning, the petitioner picks out scraps of language from a trio of reported cases. This scavenger hunt proves unproductive.

To begin, the petitioner cites In re Ayala-Arevalo, 22 I & N Dec. 398 (BIA 1998), for the proposition that an alien "who does not yet have a final order of deportation, still enjoys the status of an alien who has been 'lawfully admitted for permanent residence.' " Id. at 402. The petitioner's reliance on Ayala-Arevalo is misplaced. Wresting the quoted language from its contextual moorings and giving it sweeping effect — as the petitioner suggests — would ignore entire sections of the Act and a host of implementing regulations that specify the precise circumstances in which an alien's status as a conditional lawful permanent resident terminates. See, e.g., 8 U.S.C. § 1186a(e)(3)(C); 8 C.F.R. §§ 216.4(d)(2), 216.5(f).. We cannot — and will not — dispense in so cavalier a manner with the combined directives of Congress and DHS.

Ayala-Arevalo is inapposite for other reasons as well. The alien there enjoyed status as a lawful permanent resident, not as a conditional lawful permanent resident. See Ayala-Arevalo, 22 I & N Dec. at 399. While the petitioner argues that conditional permanent residency is equivalent in all respects to permanent residency, that argument is specious. When Congress wanted to equate the two residency statuses, it knew exactly how to write such an equivalency into the Act. See, e.g., 8 U.S.C. § 1186a(e) (providing that, for purposes of naturalization, the period of conditional lawful permanent residence should be treated as part of the period of "lawful permanent residence"). Otherwise, Congress has refrained from conflating conditional permanent residency with ordinary permanent residency.

The petitioner's embrace of the BIA's decision in Matter of Paek, 26 I & N Dec. 403 (BIA 2014), does nothing to advance her cause. That decision merely notes that (except to the extent the Act says otherwise) conditional lawful permanent residents have the same privileges as lawful permanent residents, "such status not having changed." Id. at 407. Here, however, the petitioner's status underwent a material change: her conditional residency was terminated in 1997.

So, too, the petitioner finds no succor in Gallimore v. Attorney General of the United States, 619 F.3d 216 (3d Cir.2010). The *396 petitioner quotes the GalUmore court's pronouncement that "[t]he [Act] ... equates conditional [lawful permanent residents] with 'full-fledged' [lawful permanent residents]." Id. at 229. But the' court hastened to except those situations in which "§ 1186a [of the Act] prescribes additional obligations." Id. In this instance, section 1186a pertains; and the petitioner cannot satisfy the additional obligations of section 1186a because her application for removal of her conditional status was denied. See 8 U.S.C. § 1186a(c)(3)(C).

To say more would be pointless. We hold, without serious question, that the BIA did not err in declaring the petitioner categorically ineligible for cancellation of removal under 8 U.S.C. § 1229b(a). 2

III. CONCLUSION

We need go no further. For the reasons elucidated above, we deny the petition for judicial review.

So Ordered.""")

# Case 18
add_case("""Ye Xian Jing v. Lynch
Court of Appeals for the First Circuit

Citations: 845 F.3d 38, 2017 WL 34860, 2017 U.S. App. LEXIS 138
Docket Number: 16-1290P
Judges: Lynch, Selya, Burroughs
Opinion
Authorities (18)
Cited By (9)
Summaries (2)
Similar Cases (34.2K)
PDF
Headmatter
YE Xian Jing, a/k/a Xian Jing Ye, Petitioner, v. Loretta E. LYNCH, Attorney General of the United States, Respondent.

No. 16-1290

United States Court of Appeals, First Circuit.

January 4, 2017

*40 Gerald Karikari and Karikari & Associates, P.C., New York, NY, on brief for petitioner.

Benjamin C. Mizer, Principal Deputy Assistant Attorney General, Civil Division, United States Department of Justice, Emily Anne Radford, Assistant Director, and Aric A. Anderson, Trial Attorney, Office of Immigration Litigation, on brief for respondent.

Before LYNCH and SELYA, Circuit Judges, and BURROUGHS * , District Judge.
 * Of the District of Massachusetts, sitting by designation. ↵
Combined Opinion by Burroughs
BURROUGHS, District Judge.
Ye Xian Jing a/k/a Xian Jing Ye ('Ye"), a native of China, filed a petition for review of a Board of Immigration Appeals ("BIA") decision, which dismissed his appeal of the Immigration Judge's ("IJ") de *41 nial of his applications for asylum, withholding of removal, and protection under the Convention Against Torture ("CAT"). Because the BIA's decision was supported by substantial evidence, we deny the petition.

I. BACKGROUND

On July 19, 2012, Ye, a citizen of China, entered the United States without admission or parole in Arizona. He was detained by the Department of Homeland Security ("DHS"), and interviewed (the "DHS Interview") on July 19, 2012. The record of the DHS Interview includes a three-page "Record of Sworn Statement in Proceedings Under Section 235(b)(1) of the Act" (hereinafter, the "Sworn Statement") and a one-page "Jurat for Record of Sworn Statement in Proceedings under Section 235(b)(1) of the Act" (hereinafter, the "Ju-rat"). 1

The Sworn Statement, dated July 19, 2012, indicates that a Mandarin interpreter was used, and that Ye was advised by a Border Patrol agent that "U.S. law provides protection to certain persons who face prosecution, harm or torture upon return to their home country." The Border Patrol agent also informed Ye that "[i]f you fear or have a concern about being removed from the United States or about being sent home, you should tell me so during this interview because you may not have another chance." Ye said he understood. When asked why he came to the United States, Ye answered "I just wanted to come to the United States." When asked if he wanted to add anything at the end of the interview, Ye indicated that there was nothing else he wanted to say. Despite being specifically warned that he might not have another opportunity to raise his fears or concerns regarding removal later, Ye did not raise his alleged past persecution or fear of future persecution. Ye signed all three pages of the Sworn Statement.

The Jurat, dated July 20, 2012, is also signed by Ye, and appears to be part of the same interview documented in the Sworn Statement. The Jurat contained Ye's answers to a series of questions, including that he had left China "to live and work," that he had no fear or concern about returning, and that he would not be harmed if he returned.

Thereafter, Ye expressed a fear of returning to China, and in November 2012 he was given a "credible fear interview," where he stated that when he was in China he had been arrested and beaten by Chinese authorities at an unauthorized house church and then detained for over a month. On November 14, 2012, an asylum officer determined that Ye had expressed a credible fear of persecution. He was subsequently charged with being removable as an alien seeking admission without required documents. He filed an asylum application, requested withholding of removal, and sought protection under CAT. In response, DHS submitted the July 19 and July 20, 2012 Sworn Statement and Jurat.

On September 4, 2014, the IJ held a hearing on the asylum application, request for withholding of removal, and CAT protection claim. Ye and a friend with whom he attended church in the United States testified, and he submitted a 2012 State Department report on religious freedom in China. During his testimony, Ye conceded *42 his removability, but testified that he feared religious persecution in China if he returned and that he had suffered a specific instance of religious persecution by Chinese officials in the past. Ye admitted that during the DHS Interview he had answered questions through an interpreter, that the interpreter had read back the answers, and that Ye had then signed all of the pages, indicating that the answers were accurate and truthful. Ye also testified that he had not understood all of the questions, that he had been nervous during the interview, and that he had feared he would be sent back to China for saying the "wrong thing." At no point did he distinguish between the Sworn Statement and the Jurat. The 2012 State Department report on religious freedom in China, submitted to the IJ, contained some general evidence of problems certain Christians have faced in some parts of China.

At the conclusion of the hearing, the IJ denied all of Ye's claims and ordered him removed from the United States. In support of his decision, the IJ found that Ye was not credible. Relying largely on the DHS Interview, he reasoned it was "absolutely inconceivable that if those events [being beaten and kicked by the police, arrested, and detained in China] had occurred and if indeed the respondent had left China for the sole purpose of escaping that persecution, that he would have failed to mention those events to the Border Patrol agents." The IJ found that Ye "ha[d] failed to provide a rational and reasonable explanation for his failure to state his claim to the Border Patrol agent."

Ye appealed the decision of the IJ, noting, inter alia, that the dates on the Sworn Statement and Jurat did not match. On February 18, 2016, the BIA dismissed Ye's appeal. The BIA upheld the IJ's denial of the asylum and withholding of removal applications, and concluded that Ye's CAT claim failed because "the facts do not demonstrate that the respondent would more likely than not be tortured in China by or with the acquiescence of a public official or other person acting in an official capacity." In reaching this outcome, the BIA adopted and affirmed the IJ's adverse credibility determination because "the IJ articulated specific, cogent reasons based in the record for finding that the respondent was not credible." The BIA noted that Ye raised the issue of the Jui-at's date for the first time on appeal, but concluded that he "ha[d] not shown that this affects the substance of his interview." In upholding the adverse credibility finding, the BIA emphasized that Ye had an interpreter during the DHS Interview, that he understood the interpreter, that he was re-read his answers, and that he signed the interview record attesting that his answers were truthful and accurate. The BIA additionally noted that Ye did not tell the Border Patrol agent that he was nervous or unable to understand the questions. The BIA also held that Ye's alternative argument, that despite the adverse credibility determination he had established a well-founded fear of future persecution, was not raised below, and further, that it was meritless based on the record. On March 14, 2016, Ye petitioned for review of the dismissal.

II. STANDARD OF REVIEW

"We review the decision of the BIA and 'those portions of the [IJ]'s opinion that the BIA has adopted.' " Pheng v. Holder, 640 F.3d 43, 44 (1st Cir. 2011) (quoting Romilus v. Ashcroft, 385 F.3d 1, 5 (1st Cir. 2004)). Questions of law are reviewed de novo, with appropriate deference to the agency's interpretation of the statute it administers. Romilus, 385 F.3d at 5. We review questions of fact, including credibility determinations, under the substantial evidence standard, reversing "only if 'a reasonable adjudicator would be com *43 pelled to conclude to the contrary.' " Pheng, 640 F.3d at 44 (quoting Castillo-Diaz v. Holder, 562 F.3d 23, 26 (1st Cir. 2009)) (further internal quotation marks omitted).

III. DISCUSSION

Ye has the burden of establishing eligibility for asylum, withholding of removal, or CAT protection. See Wen Feng Liu v. Holder, 714 F.3d 56, 60 (1st Cir. 2013). In his petition for review, with respect to his asylum application, Ye argues (1) that the IJ clearly erred in finding him not credible, and (2) that regardless of any adverse credibility finding, he independently established a well-founded fear of persecution. Ye makes the same arguments with respect to his application for withholding for removal. Finally, he argues that no substantial evidence supported the rejection of his CAT claim.

A. Asylum,

To qualify for asylum, an applicant must be a "refugee," who faces "persecution or [has] a well-founded fear of persecution on account of race, religion, nationality, membership in a particular social group, or political opinion" in his country of citizenship or where he "last habitually resided." 8 U.S.C. §§ 1101(a)(42)(A), 1158(b)(1)(A). "A well-founded fear of future persecution must be both subjectively authentic and objectively reasonable," so that "an alien must show that he genuinely fears persecution were he to be repatriated and that his fear has an objectively reasonable basis." Villafranca v. Lynch, 797 F.3d 91, 95 (1st Cir. 2015). A well-founded fear of persecution is presumed if the applicant establishes past persecution, but the presumption can be rebutted. 8 C.F.R. § 1208.13(b). The crux of Ye's petition is his challenge to the IJ's determination that he was not credible, and the BIA's acceptance of that adverse credibility determination. Ye also argues that, even if the adverse credibility determination stands, he established a well-founded fear of future persecution.

Credible testimony can satisfy an applicant's burden of proof, but an IJ is "entitled to evaluate the asylum-seeker's credibility." Muñoz-Monsalve v. Mukasey, 551 F.3d 1, 8 (1st Cir. 2008). Congress codified guidance on how a factfinder should make credibility determinations in such cases:

Considering the totality of the circumstances, and all relevant factors, a trier of fact may base a credibility determination on the demeanor, candor, or responsiveness of the applicant or witness, the inherent plausibility of the applicant's or witness's account, the consistency between the applicant's or witness's written and oral statements (whenever made and whether or not under oath, and considering the circumstances under which the statements were made), the internal consistency of each such statement, the consistency of such statements with other evidence of record (including the reports of the Department of State on country conditions), and any inaccuracies or falsehoods in such statements, without regard to whether an inconsistency, inaccuracy, or falsehood goes to the heart of the applicant's claim, or any other relevant factor.
8 U.S.C. § 1158(b)(l)(B)(iii). An applicant's demeanor at a hearing, which the IJ is best positioned to assess, "is often a critical factor in determining [his] truthfulness." Wen Feng Liu, 714 F.3d at 61 (quoting Laurent v. Ashcroft, 359 F.3d 59, 64 (1st Cir. 2004)). An IJ may ultimately disregard or discount incredible evidence. Pan v. Gonzales, 489 F.3d 80, 86 (1st Cir. 2007).

*44 There was substantial evidence supporting the IJ's adverse credibility determination and the BIA's acceptance of it. In supporting the determination, the IJ and BIA relied heavily on the DHS Interview and the fact that Ye omitted any mention whatsoever of past persecution, a fear of future persecution, or events that might imply such a fear despite the fact that he received a direct instruction soliciting such information and a warning that he might not have the opportunity to disclose his fear later. Further, the IJ and BIA relied specifically on the Jurat in which Ye affirmatively stated that he was not afraid of returning home and that he would not be harmed if he did so. In a situation where "petitioner has told different tales at different times," "a judge is entitled to 'sharply discount' the testimony." Muñoz-Monsalve, 551 F.3d at 8 (quoting Pan, 489 F.3d at 86). The BIA also explained in detail that Ye's testimony before the IJ supported the IJ's reliance on the DHS Interview; namely, Ye's own testimony confirmed that he understood the questions, that the interpreter read the answers back to him to verify their accuracy, and that Ye signed the interview attesting to its accuracy and truthfulness. Under § 1158(b)(l)(iii), the IJ was entitled to rely on the DHS Interview, its surrounding circumstances, the omissions it evidenced, and its inconsistency with both the subsequent credible fear interview and Ye's hearing testimony in reaching the adverse credibility determination. Because "determining credibility is a matter of sound judgment and common sense ..., when an alien's earlier statements omit any mention of a particularly significant event or datum, an IJ is justified — at least in the absence of a compelling explanation — in doubting the petitioner's veracity." Wen Feng Liu, 714 F.3d at 61 (quoting Muñoz-Monsalve, 551 F.3d at 8).

The IJ and BIA did not err in finding that Ye's explanations for the inconsistency between the DHS Interview and later claims, which included nerves, lack of understanding, and the difficult journey, were insufficiently compelling. The BIA noted that Ye never told the Border Patrol agent that he could not understand the questions or that he was too nervous to be accurate. The BIA clearly articulated its reasons for treating the DHS Interview as reliable: the interview record and Ye's subsequent testimony indicated that an interpreter was used, that Ye understood the questions asked, and that he attested to the accuracy and truthfulness of his answers. In finding Ye not credible in his explanation that he did not understand the questions, the IJ emphasized that Ye had admitted to answering at least some of the questions during the DHS Interview correctly, which undermined his claim that he could not understand what he was being asked. The IJ reasonably found it implausible that Ye would have so blatantly omitted any mention of the alleged past persecution from the DHS Interview if it had actually happened. Finally, the BIA explained that it relied on the DHS Interview despite the different dates on the Jurat and the Sworn Statement because Ye did not raise the issue of the dates before the IJ and also failed to explain why any such discrepancy substantially affected the record.
Ye next argues that the border interview was unreliable and urges us to assess its reliability under the Second Circuit standard as set forth in Ramsameachire v. Ashcroft, 357 F.3d 169, 180 (2d Cir. 2004). This Circuit does not require IJs to undertake an inquiry into the reliability of initial interviews with Border Patrol agents using specifically enumerated factors. See, e.g., Conde Cuatzo v. Lynch, 796 F.3d 153, 156 (1st Cir. 2015) (finding *45 inconsistencies across three interviews, including omissions in initial interview with Border Patrol, to support IJ's adverse credibility determination); see also Jianli Chen v. Holder, 703 F.3d 17, 23 (1st Cir. 2012) (holding that BIA could rely on a form customarily prepared by Border Patrol agents in supporting adverse credibility determination because "[i]t is normally enough if the IJ reasonably finds a proffered piece of evidence to be reliable and its use to be fundamentally fair"). Ye has failed to persuade us that the current case law in this Circuit and the applicable statutes provide insufficient guidance on making credibility determinations. Section 101(a)(3) of the REAL ID Act outlines how IJs must make credibility determinations, and was added following the decision in Ramsameachire. See REAL ID Act of 2005, Pub. L. No. 109-13, Div. B, Title I, § 101(a)(3), 119 Stat. 302, 303 (codified at 8 U.S.C. § 1158(b)(l)(B)(iii)). Section 101(a)(3) specifically allows IJs to consider "the consistency between the applicant's or witness's written and oral statements (whenever made and whether or not under oath, and considering the circumstances under which the statements were made)." 8 U.S.C. § 1158(b)(l)(B)(iii). For all the reasons already stated, including the confirmatory statements by Ye during his testimony before the IJ, the BIA's reliance on the Sworn Statement and Jurat was reasonable and supported by substantial evidence. Thus, substantial evidence supported the adverse credibility determination. Given that Ye's claim of past persecution relied on his credibility, the BIA also did not err in concluding that Ye failed to establish his eligibility for asylum based on past persecution.

Ye claims that, regardless of any adverse credibility finding, he nonetheless adequately established a well-founded fear of future persecution. The argument runs as follows: because there is a pattern or practice of persecuting Christians in China and because Ye is Christian, Ye had a well-founded fear of future persecution. The BIA noted that Ye presented this argument for the first time before the BIA. He did not argue before the IJ that, independent of his claims of past persecution, he had a well-founded fear of future persecution because there was a pattern or practice of persecuting Christians in China. Thus, the BIA did not err in concluding that the argument was not exhausted. See Kechichian v. Mukasey, 535 F.3d 15, 22 (1st Cir. 2008).

Nor did the BIA err in finding that the claim lacked merit, in any event. Asylum "solely based on [an applicant's] membership in a protected group" is only available in "some extreme cases." Rasiah v. Holder, 589 F.3d 1, 5 (1st Cir. 2009) (emphasis omitted). The standard for proving a "pattern or practice" of persecution "is demanding and in substance requires a showing of regular and widespread persecution creating a reasonable likelihood of persecution of all persons in the group." Id. at 5. Here, the only evidence submitted regarding a pattern or practice of persecution, independent of Ye's discredited testimony regarding past persecution, was the 2012 State Department report on religious freedom in China. The report, which indicates that certain Christians can avoid persecution in certain areas under certain circumstances, is not enough. See Chen Qin v. Lynch, 833 F.3d 40, 45 (1st Cir. 2016) (holding that State Department report was "not enough to establish a pattern or practice of persecution" of Christians in China). Moreover, Ye's failure to tie the report to his specific circumstances proves fatal to his argument. See id. ("Nor is [the State Department report] sufficiently related to her own situation to be persuasive."). We have repeatedly recognized that the BIA is *46 justified in concluding that there is no well-founded fear of future persecution based on a State Department report alone, when no connection is established between the incidents in the report and the petitioner's specific circumstances. See, e.g., Xian Tong Dong v. Holder, 696 F.3d 121, 126 (1st Cir. 2012) ("[OJverview reports ... 'do very little to substantiate' claims of persecution as they do not ordinarily 'either directly or by reasonable implication, connect these foibles with the petitioner's particular situation.' " (quoting Lopez Perez v. Holder, 587 F.3d 456, 461 (1st Cir. 2009))); see also Hong Chen v. Holder, 558 Fed.Appx. 11, 16 (1st Cir. 2014) (collecting cases). Thus, because he is unable to estab: lish either past persecution or a well-founded fear of future persecution, Ye's asylum claim fails.

B. Withholding of Removal

To qualify for withholding of removal, ari applicant must demonstrate that it is more likely than not that his "life or freedom would be threatened in that country because of the alien's race, religion, nationality, membership in a particular social group, or political opinion." 8 U.S.C. § 1231(b)(3)(A); 8 C.F.R. § 1208.16(b). Because the bar for withholding of removal is higher than the bar for asylum, an applicant cannot prevail on a withholding application if he fails to establish the elements of an asylum claim. Jianli Chen, 703 F.3d at 27; see also Mendez-Barrera v. Holder, 602 F.3d 21, 27 (1st Cir. 2010) ("After ah, withholding of removal requires a showing, by a clear probability, that an alien will more likely than not face persecution if repatriated."). Because his asylum claim fails, Ye's withholding of removal claim necessarily fails as well.

C. CAT Protection

Finally, CAT protection requires an applicant to demonstrate that in the proposed country of removal, "it is more likely than not that he or she would be tortured" by or with the acquiescence of the government. 8 C.F.R. § 1208.16(c)(2); Mendez-Barrera, 602 F.3d at 27. Ye failed to present any credible, "particularized facts relating to [his] specific claim that [he] would face a likelihood of government-sanctioned torture." Mendez-Barrera, 602 F.3d at 28. Besides his discredited testimony, Ye presented a country report on religious freedom in China from 2012. Country reports "are rarely disposi-tive" because of their "generic nature," id. and Ye does not persuade us that the IJ or BIA erred in their determinations. Thus, substantial evidence existed to support the BIA's rejection of Ye's CAT claim.

IV. CONCLUSION

For the foregoing reasons, the petition for review is DENIED.""")

# Case 19
add_case("""Lopez-Lopez v. Sessions
Court of Appeals for the First Circuit

Citations: 885 F.3d 49
Docket Number: 17-1907P
Judges: Lynch, Souter, Kayatta
Opinion
Authorities (3)
Cited By (4)
Summaries (3)
Similar Cases (21.8K)
PDF
Headmatter
Rony LOPEZ-LOPEZ, Petitioner,
v.
Jefferson B. SESSIONS, III, Attorney General, Respondent.
No. 17-1907
United States Court of Appeals, First Circuit.
March 16, 2018
Kevin P. MacMurray, Daniel W. Chin, and MacMurray & Associates on brief for petitioner.
David Kim, Trial Attorney, Office of Immigration Litigation, Civil Division, U.S. Department of Justice, Chad A. Readler, Acting Assistant Attorney General, and Kohsei Ugumori, Senior Litigation Counsel, Office of Immigration Litigation, on brief for respondent.
Before Lynch, Circuit Judge, Souter, Associate Justice, * and Kayatta, Circuit Judge.
 Hon. David H. Souter, Associate Justice (Ret.) of the Supreme Court of the United States, sitting by designation. ↵
Combined Opinion by Lynch
LYNCH, Circuit Judge.
We deny Rony Lopez-Lopez's petition for review because there was substantial evidence before the IJ and BIA that Lopez-Lopez had failed to meet his burden to establish a nexus between his alleged persecution and a statutorily protected ground.

In April 2013, the Department of Homeland Security served Lopez-Lopez, a native and citizen of Guatemala, with a notice to appear, charging that he was removable pursuant to 8 U.S.C. § 1182 (a)(6)(A)(i) because he had entered the United States without inspection on an unknown date; Lopez-Lopez later testified that he had entered in January 2007. Lopez-Lopez filed an application for asylum, withholding of removal, and protection under the Convention Against Torture ("CAT") in March 2015. The immigration judge ("IJ") excused the late filing of Lopez-Lopez's application, and addressed and denied it on its merits.

Lopez-Lopez claimed that his basis for relief was that drug traffickers had moved into his village in Guatemala in 2006, taken over his family's land, and used threats of violence to coerce him and his family members into cultivating raw materials for drugs on that land. Lopez-Lopez also testified that three of his siblings remained unharmed in Guatemala because they did what the drug traffickers asked them to do. He alleged that he had been persecuted, and that the persecution was because he belonged to a "particular social group" of "poor, uneducated landowners."

The IJ denied Lopez-Lopez's application, holding that his claimed social group was "not a protected ground under the [Immigration and Nationality Act]" and that, in any case, Lopez-Lopez had not established a nexus between his alleged persecution, or fear of future persecution, and any protected ground. The IJ also held that, even if Lopez-Lopez had established that he had been targeted on the basis of a protected ground, he had failed to show government action or inaction necessary to establish past persecution because "there was no evidence that any Guatemalan authorities on any level were notified of the situation." 1

On appeal, the BIA agreed with the IJ's conclusion that Lopez-Lopez had not "establish[ed] that any persecution he ha[d] suffered or fears was or is on account of a protected ground." The BIA held that, even assuming that Lopez-Lopez had established a "cognizable particular social group" of "poor, uneducated landowners in Guatemala," he had "not demonstrated that one central motive for the harm he suffered or fears was or would be on account of his membership in such a group." The BIA also stated that "widespread violence" in Guatemala "d[id] not provide a basis for a grant of asylum." Because the BIA's nexus holding was an independently sufficient basis for its decision to dismiss Lopez-Lopez's appeal, the BIA did not, and was not obligated to, address the other bases for the IJ's decision, contrary to Lopez-Lopez's arguments in his petition for review. See INS v. Bagamasbad , 429 U.S. 24 , 25, 97 S.Ct. 200 , 50 L.Ed.2d 190 (1976) ("As a general rule courts and agencies are not required to make findings on issues the decision of which is unnecessary to the results they reach.").

In his petition for review, Lopez-Lopez argues that he met his burden of establishing both nexus to a protected ground and past persecution. We reach only the nexus issue.

We review the IJ's and BIA's nexus determination "through the prism of the substantial evidence rule," Lopez de Hincapie v. Gonzales , 494 F.3d 213 , 218 (1st Cir. 2007), under which we uphold the determination unless the record " compel[s] the contrary conclusion," id. Lopez-Lopez testified that drug traffickers had "t[aken] advantage" of his family's land because it was "very productive." He also testified that the drug traffickers had forced him and his family members to cultivate raw materials for drugs on that land because his family "had experience with agriculture and harvest[ing]." Based on this testimony, the IJ and BIA reasonably concluded that the drug traffickers' alleged conduct had been centrally motivated by a desire to profit from the use of Lopez-Lopez's family's land, rather than by an intent to harm poor, uneducated landowners as a group. See Singh v. Mukasey , 543 F.3d 1 , 6-7 (1st Cir. 2008) (holding that evidence that the petitioner had been persecuted "primarily" because of "economic motivations" supported the BIA's finding that petitioner had failed to show nexus); Lopez de Hincapie , 494 F.3d at 219 (holding that facts indicating that petitioner had been targeted "because of greed, not because of her political opinion or membership in a particular social group," supported the BIA's determination that petitioner had not established nexus). As such, substantial evidence supported the BIA's and IJ's dispositive determination that Lopez-Lopez had failed to establish a nexus between the persecution that he allegedly had suffered, or any future persecution that he fears that he will suffer, and a statutorily protected ground. The petition for review is denied .""")

if __name__ == "__main__":
    if len(cases_to_process) == 19:
        process_all_cases()
    else:
        print(f"Ready to collect cases. Currently have {len(cases_to_process)}/19 cases.")
        print("Add cases using: add_case(case_text, url)")
        print("When all 19 are added, run: process_all_cases()")
