import { readFileSync } from "fs";
import { Connection, Keypair, PublicKey } from "@solana/web3.js";
import { getMint, getOrCreateAssociatedTokenAccount, mintTo } from "@solana/spl-token";

// Read config & keys (strip BOM if present)
const cfg = JSON.parse(readFileSync("C:\\Users\\ruben\\Documents\\optiloves-backend\\chain.config.json","utf8").replace(/^\uFEFF/,""));
const secret = Uint8Array.from(JSON.parse(readFileSync("C:\\Users\\ruben\\Documents\\optiloves-backend\\keys\\treasury.json","utf8")));
const kp = Keypair.fromSecretKey(secret);
const conn = new Connection(cfg.rpc, "confirmed");

// Amount (UI units) -> RAW using on-chain decimals
const UI = 0n; // 100 tokens; change as needed

(async () => {
  const mintPub = new PublicKey(cfg.mint);
  const mi = await getMint(conn, mintPub);
  const decimals = mi.decimals ?? 6;
  const RAW = UI * (10n ** BigInt(decimals));

  const ata = await getOrCreateAssociatedTokenAccount(conn, kp, mintPub, kp.publicKey);
  await mintTo(conn, kp, mintPub, ata.address, kp.publicKey, RAW);
  console.log("Minted", UI.toString(), "tokens to", ata.address.toBase58(), "(raw:", RAW.toString(), ")");
})();