\# TrainSurf — Smart Seat-Hop Search for Indian Railways



TrainSurf is a developer-built, algorithm-driven project that explores a real-world problem faced by Indian Railways passengers: direct tickets often show unavailable even when a journey is still possible by intelligently booking shorter segments on the same train.



This project was designed and implemented during my free time as a student developer, motivated by personal experience as a frequent hostel traveller.



---



\## Developer



\*\*Jaya Soorya\*\*  

📧 Email: amjayasoorya@gmail.com  

📞 Phone: +91 9345259635  

🔗 GitHub: https://github.com/amsoorya



---



\## Real Problem and Motivation



I am a hosteller, and trains are usually my default mode of transport.



During one such journey, every direct ticket from my source to destination showed unavailable. I tried nearby stations as well, but still had no luck. Out of necessity, I manually checked segment-wise availability within the same train:



\- Source to next station

\- That station to next

\- And so on…



Surprisingly, I was able to complete my entire journey by booking multiple short segments on the same train. I ended up doing around four seat hops across nearly ten stations, but it worked and got me home.



That experience led to an important realization:



> Existing railway apps like ixigo, ConfirmTkt, etc. do not attempt this computation at all.



The reason is understandable — the search space grows quickly and can be computationally heavy. But with the right techniques such as pruning, memoization, and priority-based search, it becomes manageable.



This insight became the foundation of TrainSurf.



---



\## What TrainSurf Does



Given:

\- Train number

\- Source station

\- Destination station

\- Travel date

\- Class type

\- Quota



TrainSurf automatically:



1\. Fetches the entire route of the train

2\. Checks seat availability for all valid station pairs along the route

3\. Models the problem as a graph traversal task

4\. Detects overlapping and stitchable segments

5\. Computes the minimum number of seat hops needed to complete the journey

6\. Outputs a clear booking plan for the user



The result is a journey that may not be directly available, but is still practically achievable.



---



\## Algorithmic Approach (High-Level)



\- Treat stations as nodes in a graph

\- Treat available seat segments as directed edges

\- Use:

&nbsp; - Memoization to avoid duplicate API calls

&nbsp; - Parallel execution to control latency

&nbsp; - Priority for longer segments first

&nbsp; - Overlap-aware stitching to reduce transfers



Finally, all valid paths are evaluated and the path with minimum transfers is selected.



This is not a brute-force search — it is a carefully pruned and optimized solution to a real constraint.



---



\## Implementation Details



\- \*\*Language:\*\* Python

\- \*\*Framework:\*\* Streamlit (for interactive UI)

\- \*\*Architecture:\*\* Client-side UI + external Railway APIs

\- \*\*Concurrency:\*\* ThreadPoolExecutor for parallel segment checks



The entire logic is implemented in a single, readable codebase (`app.py`) for clarity and evaluation.



---



\## APIs Used (Credits)



This project uses public APIs accessed via RapidAPI. All credit for railway data goes to the respective providers.



\### 1. IRCTC Train API — Train details and route



\*\*Provider:\*\* QuantumBits / IRCTC Train API  

🔗 https://rapidapi.com/quantumbits1011/api/irctc-train-api/



\### 2. IRCTC Seat Availability API



\*\*Provider:\*\* IRCTCAPI  

🔗 https://rapidapi.com/IRCTCAPI/api/irctc1/



⚠️ \*\*Note:\*\* I am currently using free-tier API plans. This project was built in my free time, so I have not yet purchased higher-tier plans. I plan to upgrade and further optimize API usage in future iterations.



---



\## How to Run Locally



```bash

git clone https://github.com/amsoorya/TrainSurf.git

cd TrainSurf

pip install -r requirements.txt

streamlit run app.py

```



You will need a RapidAPI key to test the application.



---



\## Demo Assets



\- A screen-recorded demo (`demo.mp4`)

\- UI screenshot (`screenshot.png`)



Both are included in the `assets/` folder of the repository.



---



\## Disclaimer



\- This project does not bypass IRCTC systems

\- It relies entirely on third-party APIs for data

\- Seat availability accuracy depends on API responses

\- This is an educational and exploratory project, not an official IRCTC product



---



\## Future Improvements



\- Persistent caching to reduce API cost

\- Smarter pruning strategies

\- Cost-aware search planning

\- UI performance enhancements

\- Migration to paid API tiers



---



\## Final Note for Reviewers



TrainSurf is not a clone or a UI demo.



It is a problem-first project, built from a real-life constraint, demonstrating:



\- Analytical thinking

\- Algorithm design

\- Practical API usage

\- Trade-off awareness

\- Clean, explainable implementation



I built this project independently during my free time and would be happy to discuss the approach, decisions, and limitations in detail.



Thank you for taking the time to review my work.

