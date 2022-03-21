# VMC

The Vocal Maturity Coder (VMC) is a component of the utterance level processing system (ULP), developed at Purdue University for the specific purpose of integrating automated speaker diarization output from daylong audio recordings with strategic, rapid human coding to generate key metrics of early vocal features that assist in mapping the early language trajectories of infants with intellectual and developmental disabilities. The VMC itself provides a user interface for the annotation of child utterances extracted from daylong audio recordings, as well as a database for storing and exporting these annotations to be used for data analysis. 

The VMC is designed to function using daylong audio recordings from the Language ENvironment Analysis system. The VMC utilizes three files associated with the LENA recording: 1) the interpreted time segment (.its) file, 2) a .csv export of automated LENA variables broken down by five-minute intervals, and 3) the .wav audio file of the daylong recording.  

The VMC excludes times during during the recording in which the child was taking a nap or times that the parent indicated they would like removed from the .wav recording. The VMC then uses the .csv file to identify the ten five-minute segments of highest volubility across the recording (i.e., the ten five-minute segments during which the child was vocalizing the most, as indicated by the five-minute segment’s CV_COUNT variable in the .csv file). From the remaining five-minute segments, the VMC randomly selects 20 additional segments, regardless of volubility. 

After identifying the 30 five-minute segments, the VMC then uses the .its file to identify child utterances that started during these selected five-minute segments. The VMC selects only sound events from the .its file that are tagged as the target child (labeled by LENA as “CHN”). It does not include vocalizations tagged as faint child vocalizations (labeled by LENA as “CHF”). 

After identifying the CHN utterances from the designated five-minute segments, the VMC used the start and stop time of the CHN utterances from the .its file to segment the .wav file into individual utterance audio clips.  The VMC also creates a dataset that estimates the minimum, maximum, and average pitch of each individual utterance audio clip using Praat. 

Utterance audio clips are then placed in a queue to be presented individually to trained coders to annotate using a coding interface:
![VMCv2_base anonymous](https://user-images.githubusercontent.com/51832232/159368789-3605dc9c-faa3-4457-87e2-72aed4ac72c2.jpeg)

The coding interface randomly presents utterance clips to a single coder, who can listen to the utterance as many times as necessary to annotate the clip. Coders first decide whether the utterance is a Cry, Laugh, Non-Canonical syllable, Canonical syllable, or a Word. Coders select the highest level of vocal maturity present in the utterance. For Non-Canonical utterances, coders are asked how many total syllables were in the utterance. For Canonical utterances, they are asked (1) how many Canonical syllables and (2) how many total syllables (Canonical + Non-Canonical) are in the utterance. For Word utterances, coders are asked (1) how many Words, (2) how many Word syllables, (3) how many Canonical syllables, and (4) how many total syllables (Word + Canonical + Non-Canonical) are in the utterance. 
Coders are also given a “Don’t Code” annotation option to use if the utterance does not sound like an utterance made by the target child, or if there is significant overlapping speech or other noise in the background that would significantly impact the pitch reading of the vocalization. After confirming their selections, coders submit their annotation and move to the next utterance to code. Each utterance is annotated by three different coders.

Annotations are stored in a database established by the user (i.e., not included in the VMC). Python scripts are included in the VMC to aid in extracting and summarizing data at the utterance- or child-level. 

Please contact Bridgette Kelleher (bkelleher@purdue.edu) for more information. 

