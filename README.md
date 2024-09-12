# CS50 Banks

## [Demonstration Video](https://youtu.be/qyrX7hFzwEQ)

## Description:
1. Register: On this page, the user will have to provide their first name, last name, username, email address and password. Both their username and email address have to be unique. This is fictional, so they do not have to enter any credit card information.

2. Sign In: If the user doesn't have a session/cookies, they will be by default redirected here to sign into their account using their username and password. Both are of course checked by the back end by querying the database.

3. Home: On the homepage, the balance of the user is displayed as well as their pending money requests, which they can either accept - which will automatically send the indicated amount to the sender - or decline. Either option will log this into the activity history.

4. Transfers: Three options are displayed here: send money, request money or edit balance.

5. Send: To send money, the user must enter a valid recipient username, a valid amount (> 0 and < user's balance), a reason for their sending (optional) and their password for security reasons. If all requirements are met, the money will be sent to the other user and it will be logged in the transactions table of the SQLite database, accessible in history.

6. Request: The same fields are required to do this. This will send a request that the other user will see on their homepage and will be able to accept/decline.

7. Edit: Since this web app is fictional, this is the user's ability to add or remove money to their balance. The only field is the amount.

8. Loans: As a simulation, the user is able to loan money from the bank. They must specify and amount of money, a duration in days, a reason (optional) and their password. A 10% interest rate is applied to any user who wants to borrow money.
   Under the form, there is a table listing all the current loans to which the user is committed. (Amount, interest rate, duration, reason and start date.)

9. History: On this page, the user has access to all the impacting actions they have performed since the creation of their account, such as sending money, requesting money, editting their balance, loaning money, paying their loan back, accepting/refusing a request received...

10. Settings: The user's profile information is displayed above three buttons: toggle theme, delete account and sign out.

11. Toggle theme: This simply enables/disables the darker theme.

12. Delete account: This deletes the user's account but keep their data as it can still be used by other users if they have interacted with them in the past.

13. Sign out: This deletes the user's session/cookies and redirects them to the sign in page.

14. Footer: The user can see which account they are logged into.