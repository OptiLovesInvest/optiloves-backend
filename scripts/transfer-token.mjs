import { readFileSync } from "fs";
import { Connection, Keypair, PublicKey, LAMPORTS_PER_SOL } from "@solana/web3.js";
import { getMint, getOrCreateAssociatedTokenAccount, transfer } from "@solana/spl-token";

const cfg = JSON.parse(readFileSync("C:\\Users\\ruben\\Documents\\optiloves-backend\\chain.config.json","utf8").replace(/^\uFEFF/,""));
const secret = Uint8Array.from(JSON.parse(readFileSync("C:\\Users\\ruben\\Documents\\optiloves-backend\\keys\\treasury.json","utf8")));
const kp = Keypair.fromSecretKey(secret);
const conn = new Connection(cfg.rpc, "confirmed");

function die(msg){ console.error(msg); process.exit(1); }
const [,, toArg, uiArg] = process.argv;
if (!toArg || !uiArg) die("Usage: node scripts/transfer-token.mjs <RECIPIENT_PUBKEY> <AMOUNT_UI>");

(async () => {
  const to = new PublicKey(toArg);
  const mintPub = new PublicKey(cfg.mint);

  // ensure fee SOL
  const bal = await conn.getBalance(kp.publicKey);
  if (bal < 0.2*LAMPORTS_PER_SOL) { console.warn("Low SOL for fees:", bal/LAMPORTS_PER_SOL); }

  const mi = await getMint(conn, mintPub);
  const decimals = mi.decimals ?? 6n;
  const ui = BigInt(Math.floor(Number(uiArg)));                 // integer UI units for MVP
  const raw = ui * (10n ** BigInt(decimals));

  const fromAta = await getOrCreateAssociatedTokenAccount(conn, kp, mintPub, kp.publicKey);
  const toAta   = await getOrCreateAssociatedTokenAccount(conn, kp, mintPub, to);
  await transfer(conn, kp, fromAta.address, toAta.address, kp.publicKey, raw);

  console.log("Sent", ui.toString(), "tokens to", to.toBase58(), "raw:", raw.toString());
})();