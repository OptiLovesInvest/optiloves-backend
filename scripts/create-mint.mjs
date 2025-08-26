import { writeFileSync, existsSync, readFileSync } from "fs";
import { Connection, Keypair, LAMPORTS_PER_SOL, clusterApiUrl } from "@solana/web3.js";
import { createMint, getOrCreateAssociatedTokenAccount, mintTo, getMint } from "@solana/spl-token";

const cfgPath = "C:\\Users\\ruben\\Documents\\optiloves-backend\\chain.config.json";
const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
const RPC = cfg.rpc || clusterApiUrl(cfg.cluster || "devnet");
const DECIMALS = 6;               // keep 6 for MVP
const INITIAL_UI = 100;             // set >0 if you want to pre-mint to treasury

function toRaw(ui, d){ return BigInt(Math.round(ui * 10 ** d)); }

const kpPath = "C:\\Users\\ruben\\Documents\\optiloves-backend\\keys\\treasury.json";
let treasury;
if (existsSync(kpPath)) {
  const secret = Uint8Array.from(JSON.parse(readFileSync(kpPath, "utf8")));
  treasury = Keypair.fromSecretKey(secret);
} else {
  treasury = Keypair.generate();
  writeFileSync(kpPath, JSON.stringify(Array.from(treasury.secretKey)));
  console.log("Saved new treasury key:", kpPath);
}

const conn = new Connection(RPC, "confirmed");

async function ensureAirdrop(pub) {
  const bal = await conn.getBalance(pub);
  if (bal >= 0.5 * LAMPORTS_PER_SOL) return;
  console.log("Airdropping 2 SOL on devnet...");
  const sig = await conn.requestAirdrop(pub, 2 * LAMPORTS_PER_SOL);
  await conn.confirmTransaction(sig, "confirmed");
}

(async () => {
  console.log("RPC:", RPC);
  console.log("Treasury:", treasury.publicKey.toBase58());
  await ensureAirdrop(treasury.publicKey);

  console.log("Creating mint (decimals =", DECIMALS, ")...");
  const mintPubkey = await createMint(
    conn,
    treasury,                 // payer
    treasury.publicKey,       // mint authority
    treasury.publicKey,       // freeze authority
    DECIMALS
  );
  console.log("Mint:", mintPubkey.toBase58());

  console.log("Creating ATA for treasury...");
  const ata = await getOrCreateAssociatedTokenAccount(conn, treasury, mintPubkey, treasury.publicKey);
  console.log("Treasury ATA:", ata.address.toBase58());

  const raw = toRaw(INITIAL_UI, DECIMALS);
  if (raw > 0n) {
    console.log("Minting initial tokens:", INITIAL_UI, "(raw:", raw.toString(), ")");
    await mintTo(conn, treasury, mintPubkey, ata.address, treasury.publicKey, raw);
  }

  const mi = await getMint(conn, mintPubkey);
  console.log("Supply (raw):", mi.supply.toString());

  // Update chain.config.json
  const updated = { ...cfg, mint: mintPubkey.toBase58(), treasury: treasury.publicKey.toBase58() };
  writeFileSync(cfgPath, JSON.stringify(updated, null, 2));
  console.log("Updated", cfgPath);
})();
