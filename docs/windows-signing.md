# Signing the Windows download

The normal Windows build produces an unsigned EXE. The manual **Sign published Windows companion** workflow takes the existing Windows EXE and its manifest from the selected commit on `main`. It compares the EXE with the published SHA-256 before signing, and publishes a separate Actions artifact only after Windows validates the signature, timestamp and expected publisher. It does not replace the public download.

1. In your Azure subscription, complete publisher identity validation for [Microsoft Artifact Signing](https://learn.microsoft.com/en-us/azure/artifact-signing/overview) and create a **Public Trust** certificate profile.
2. In GitHub, create a `windows-signing` environment restricted to `main`. Set up [GitHub OIDC federation](https://github.com/Azure/artifact-signing-action/blob/main/docs/OIDC.md) for this exact repository and environment. Assign the **Artifact Signing Certificate Profile Signer** role at the certificate profile scope. Do not upload or share a private key.
3. Set these environment variables in GitHub:
   - `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`: Azure workload identity identifiers.
   - `ARTIFACT_SIGNING_ENDPOINT`, `ARTIFACT_SIGNING_ACCOUNT`, `ARTIFACT_SIGNING_PROFILE`: the endpoint, account name and Public Trust profile name from Azure.
   - `ARTIFACT_SIGNING_PUBLISHER`: the full Authenticode signer certificate Subject as shown by Windows, including the distinguished-name fields.
4. Run the signing workflow from `main`. Download the signed artifact and test it on a clean Windows PC using its normal security settings. Compare the published SHA-256 and check the signature and publisher in **Properties → Digital Signatures**, or use `Get-AuthenticodeSignature .\ZDesk.exe` in PowerShell.
5. Publish the verified EXE and its matching new manifest together if replacing the public download. Do not use an unsigned build manifest or checksum with the signed file.

A valid publisher signature does not guarantee SmartScreen reputation or eliminate malware detections. If Defender flags a verified release incorrectly, submit that exact file and detection details to the [Microsoft Security Intelligence submission portal](https://www.microsoft.com/en-us/wdsi/filesubmission).
